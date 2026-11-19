"""Eval for the "urgent emails" LLM step: how well does the prompt pick out the urgent emails?

Run from backend/ (uses the real Gemini key from backend/.env, like demo_llm.py):
    python -m evals.run_eval
    python -m evals.run_eval --prompt-file my_prompt.txt --out results/v2.json

A prompt file is a template that must contain {{n1.output.payload.emails}}, exactly like the
prompt in examples/urgent_emails.json. The emails are filled in by the real render() function.

The functions above main() are pure (no network), so tests/test_eval_scoring.py can check them.
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.engine.nodes.llm import LLMPrompt
from app.engine.providers import plug_in_providers
from app.engine.templating import PLACEHOLDER, render

EVALS_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = EVALS_DIR / "urgent_emails.json"
EXAMPLE_WORKFLOW = EVALS_DIR.parent.parent / "examples" / "urgent_emails.json"
EMAILS_REF = "n1.output.payload.emails"

Email = dict[str, Any]


# ---------- pure functions ----------


def normalize(text: str) -> str:
    """The form used for matching: no outer spaces, case ignored."""
    return text.strip().casefold()


def validate_dataset(emails: list[Email]) -> None:
    """Ids must be unique, and texts must be unique after normalize(), or matching would be ambiguous."""
    ids: set[str] = set()
    texts: set[str] = set()
    for email in emails:
        if not isinstance(email.get("id"), str) or not isinstance(email.get("text"), str):
            raise ValueError(f"every email needs a string id and text: {email}")
        if not isinstance(email.get("urgent"), bool):
            raise ValueError(f"email {email['id']}: 'urgent' must be true or false")
        if email["id"] in ids:
            raise ValueError(f"duplicate id: {email['id']}")
        key = normalize(email["text"])
        if key in texts:
            raise ValueError(f"email {email['id']}: same text as another email")
        ids.add(email["id"])
        texts.add(key)


def match_predictions(batch: list[Email], returned: list[Any]) -> tuple[list[str], list[str]]:
    """Map the strings the model returned back to email ids from THIS batch.

    Returns (matched_ids, invented). A string must equal an email's text after normalize().
    Anything else (a reworded email, a made-up one, a non-string item) is "invented".
    Repeated answers count once.
    """
    by_text = {normalize(e["text"]): e["id"] for e in batch}
    matched: list[str] = []
    invented: list[str] = []
    seen: set[str] = set()
    for item in returned:
        text = item if isinstance(item, str) else json.dumps(item)
        key = normalize(text)
        if key in seen:
            continue
        seen.add(key)
        if isinstance(item, str) and key in by_text:
            matched.append(by_text[key])
        else:
            invented.append(text)
    return matched, invented


def ratio(numerator: int, denominator: int) -> float | None:
    """None (shown as n/a) instead of dividing by zero."""
    return None if denominator == 0 else numerator / denominator


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score(emails: list[Email], predicted_ids: list[str], invented_count: int = 0) -> dict[str, Any]:
    """Compare the predicted urgent ids with the labels.

    precision        = TP / (TP + FP)                  (invented strings left out)
    strict_precision = TP / (TP + FP + invented_count) (each invented string counts as a false positive)
    """
    all_ids = {e["id"] for e in emails}
    predicted = set(predicted_ids)
    unknown = predicted - all_ids
    if unknown:
        raise ValueError(f"predicted ids not in the dataset: {sorted(unknown)}")

    urgent = {e["id"] for e in emails if e["urgent"]}
    tp = len(predicted & urgent)
    false_positives = sorted(predicted - urgent)
    false_negatives = sorted(urgent - predicted)
    precision = ratio(tp, tp + len(false_positives))
    recall = ratio(tp, len(urgent))
    return {
        "tp": tp,
        "fp": len(false_positives),
        "fn": len(false_negatives),
        "invented": invented_count,
        "precision": precision,
        "recall": recall,
        "f1": f1_score(precision, recall),
        "strict_precision": ratio(tp, tp + len(false_positives) + invented_count),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def build_prompt(template: str, batch: list[Email]) -> str:
    """Fill the template with this batch's email texts, the same way a real run does."""
    refs = [m.group(1) for m in PLACEHOLDER.finditer(template)]
    if EMAILS_REF not in refs:
        raise ValueError(f"the prompt must contain {{{{{EMAILS_REF}}}}}")
    context = {"n1": {"output": {"payload": {"emails": [e["text"] for e in batch]}}}}
    prompt = render(template, context)
    # A template that is ONLY the placeholder renders to the raw list; turn it into text like the rest.
    return prompt if isinstance(prompt, str) else json.dumps(prompt)


def batches(items: list[Email], size: int) -> list[list[Email]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def shuffled(emails: list[Email], seed: int) -> list[Email]:
    """A mixed order, so no batch is all urgent or all not, but the same seed always gives the same order."""
    mixed = list(emails)
    random.Random(seed).shuffle(mixed)
    return mixed


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def format_report(result: dict[str, Any]) -> str:
    s = result["scores"]
    lines = [
        f"model {result['model']}, {result['email_count']} emails in batches of {result['batch_size']}",
        "",
        f"precision         {fmt(s['precision'])}   (TP {s['tp']}, FP {s['fp']})",
        f"strict precision  {fmt(s['strict_precision'])}   (invented strings counted as false positives)",
        f"recall            {fmt(s['recall'])}   (FN {s['fn']})",
        f"F1                {fmt(s['f1'])}",
        f"invented strings  {s['invented']}",
        "",
        f"false positives ({len(result['false_positives'])}):",
        *[f"  {e['id']}  {e['text']}" for e in result["false_positives"]],
        f"false negatives ({len(result['false_negatives'])}):",
        *[f"  {e['id']}  {e['text']}" for e in result["false_negatives"]],
        f"invented ({len(result['invented'])}):",
        *[f"  {text!r}" for text in result["invented"]],
    ]
    if result["warnings"]:
        lines += ["", "warnings:", *[f"  {w}" for w in result["warnings"]]]
    lines += ["", f"total tokens: {result['tokens_used']}"]
    return "\n".join(lines)


# ---------- loading files ----------


def load_dataset(path: Path) -> list[Email]:
    emails = json.loads(path.read_text())
    validate_dataset(emails)
    return emails


def load_default_config() -> dict[str, Any]:
    """The llm.prompt step of examples/urgent_emails.json: its prompt, output_schema and max_tokens."""
    workflow = json.loads(EXAMPLE_WORKFLOW.read_text())
    node = next(n for n in workflow["graph"]["nodes"] if n["type"] == "llm.prompt")
    return dict(node["config"])


# ---------- the real run ----------


class BatchFailed(Exception):
    def __init__(self, index: int, total: int, batch: list[Email], error: Exception):
        self.index, self.total, self.batch, self.error = index, total, batch, error
        super().__init__(
            f"batch {index} of {total} ({batch[0]['id']}..{batch[-1]['id']}) failed: {type(error).__name__}: {error}"
        )


async def run_eval(emails: list[Email], config: dict[str, Any], batch_size: int, seed: int) -> dict[str, Any]:
    """Ask the real LLM step about each batch. Raises BatchFailed on the first failed call."""
    llm = LLMPrompt()
    groups = batches(shuffled(emails, seed), batch_size)
    predicted: list[str] = []
    invented: list[str] = []
    warnings: list[str] = []
    tokens = 0

    for index, batch in enumerate(groups, start=1):
        step_config = {
            "prompt": build_prompt(config["prompt"], batch),
            "output_schema": config.get("output_schema"),
            "max_tokens": config.get("max_tokens", 500),
        }
        print(f"batch {index} of {len(groups)}: {batch[0]['id']}..{batch[-1]['id']}", file=sys.stderr)
        try:
            out = await llm.run(step_config, {})
        except Exception as exc:
            raise BatchFailed(index, len(groups), batch, exc) from exc

        tokens += out["tokens_used"]
        reply = out["json"]
        returned = reply.get("urgent") if isinstance(reply, dict) else None
        if not isinstance(returned, list):
            warnings.append(
                f"batch {index}: reply had no 'urgent' list, counted as nothing predicted. Reply: {out['text'][:200]!r}"
            )
            returned = []
        ids, made_up = match_predictions(batch, returned)
        predicted += ids
        invented += made_up

    by_id = {e["id"]: e for e in emails}
    scores = score(emails, predicted, len(invented))
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "model": get_settings().llm_model,
        "prompt": config["prompt"],
        "output_schema": config.get("output_schema"),
        "max_tokens": config.get("max_tokens", 500),
        "email_count": len(emails),
        "batch_size": batch_size,
        "seed": seed,
        "batches": [[e["id"] for e in batch] for batch in groups],
        "scores": {k: v for k, v in scores.items() if k not in ("false_positives", "false_negatives")},
        "false_positives": [{"id": i, "text": by_id[i]["text"]} for i in scores["false_positives"]],
        "false_negatives": [{"id": i, "text": by_id[i]["text"]} for i in scores["false_negatives"]],
        "invented": invented,
        "warnings": warnings,
        "tokens_used": tokens,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score the urgent-emails LLM prompt against labelled emails.")
    parser.add_argument("--prompt-file", type=Path, help="prompt template to try instead of the example's prompt")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="labelled emails (JSON list)")
    parser.add_argument("--batch-size", type=int, default=10, help="emails per LLM call (default 10)")
    parser.add_argument("--seed", type=int, default=42, help="shuffle seed for mixing the batches (default 42)")
    parser.add_argument("--out", type=Path, help="also save the full result as JSON here")
    args = parser.parse_args(argv)
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    return args


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    emails = load_dataset(args.dataset)
    config = load_default_config()
    if args.prompt_file:
        config["prompt"] = args.prompt_file.read_text().strip()
    build_prompt(config["prompt"], emails[:1])  # fail on a bad template before spending any tokens

    if not get_settings().llm_api_key:
        print("LLM_API_KEY is not set (backend/.env), so there is no model to evaluate.", file=sys.stderr)
        return 1
    plug_in_providers()

    try:
        result = await run_eval(emails, config, args.batch_size, args.seed)
    except BatchFailed as exc:
        print(f"\nSTOPPED: {exc}\nNo score printed, because it would only cover part of the emails.", file=sys.stderr)
        return 1

    print(format_report(result))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nsaved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
