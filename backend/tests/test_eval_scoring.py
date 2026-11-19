"""Offline tests for the eval's matching and scoring (evals/run_eval.py). No API calls."""

import json

import pytest

from evals.run_eval import (
    DEFAULT_DATASET,
    batches,
    build_prompt,
    f1_score,
    fmt,
    load_dataset,
    load_default_config,
    match_predictions,
    parse_args,
    score,
    shuffled,
    validate_dataset,
)

BATCH = [
    {"id": "e01", "text": "Server is down!", "urgent": True},
    {"id": "e02", "text": "Lunch on Friday?", "urgent": False},
    {"id": "e03", "text": "Card charged 40 times", "urgent": True},
]


# ---------- matching ----------


def test_exact_match():
    assert match_predictions(BATCH, ["Server is down!"]) == (["e01"], [])


def test_match_ignores_case_and_outer_spaces():
    assert match_predictions(BATCH, ["  server IS DOWN!  ", "card charged 40 TIMES\n"]) == (["e01", "e03"], [])


def test_unknown_string_is_invented():
    matched, invented = match_predictions(BATCH, ["Server is down!", "Database outage email"])
    assert matched == ["e01"]
    assert invented == ["Database outage email"]


def test_reworded_email_is_invented_not_matched():
    assert match_predictions(BATCH, ["Server is down"]) == ([], ["Server is down"])


def test_non_string_items_are_invented():
    assert match_predictions(BATCH, [3, {"text": "Server is down!"}]) == ([], ["3", '{"text": "Server is down!"}'])


def test_repeated_answers_count_once():
    matched, invented = match_predictions(BATCH, ["Server is down!", "server is down!", "made up", "MADE UP"])
    assert matched == ["e01"]
    assert invented == ["made up"]


def test_email_from_another_batch_is_invented():
    other_batch = [{"id": "e11", "text": "Weekly newsletter", "urgent": False}]
    assert match_predictions(BATCH, ["Weekly newsletter"]) == ([], ["Weekly newsletter"])
    assert match_predictions(other_batch, ["Weekly newsletter"]) == (["e11"], [])


def test_empty_answer():
    assert match_predictions(BATCH, []) == ([], [])


# ---------- scoring ----------


def test_score_counts_and_lists():
    emails = [
        {"id": "e01", "text": "a", "urgent": True},
        {"id": "e02", "text": "b", "urgent": True},
        {"id": "e03", "text": "c", "urgent": True},
        {"id": "e04", "text": "d", "urgent": False},
        {"id": "e05", "text": "e", "urgent": False},
    ]
    s = score(emails, ["e01", "e02", "e04"])
    assert (s["tp"], s["fp"], s["fn"]) == (2, 1, 1)
    assert s["false_positives"] == ["e04"]
    assert s["false_negatives"] == ["e03"]
    assert s["precision"] == pytest.approx(2 / 3)
    assert s["recall"] == pytest.approx(2 / 3)
    assert s["f1"] == pytest.approx(2 / 3)
    assert s["strict_precision"] == pytest.approx(2 / 3)


def test_strict_precision_counts_invented_as_false_positives():
    s = score(BATCH, ["e01", "e03"], invented_count=2)
    assert s["precision"] == 1.0
    assert s["strict_precision"] == 0.5
    assert s["invented"] == 2


def test_perfect_score():
    s = score(BATCH, ["e01", "e03"])
    assert (s["precision"], s["recall"], s["f1"]) == (1.0, 1.0, 1.0)


def test_no_predictions_gives_na_precision():
    s = score(BATCH, [])
    assert s["precision"] is None
    assert s["strict_precision"] is None
    assert s["recall"] == 0.0
    assert s["f1"] is None


def test_only_invented_gives_zero_strict_precision():
    s = score(BATCH, [], invented_count=3)
    assert s["precision"] is None
    assert s["strict_precision"] == 0.0


def test_no_urgent_labels_gives_na_recall():
    not_urgent = [{"id": "e02", "text": "Lunch on Friday?", "urgent": False}]
    s = score(not_urgent, ["e02"])
    assert s["recall"] is None
    assert s["precision"] == 0.0
    assert s["f1"] is None


def test_nothing_to_find_and_nothing_found():
    not_urgent = [{"id": "e02", "text": "Lunch on Friday?", "urgent": False}]
    s = score(not_urgent, [])
    assert (s["precision"], s["recall"], s["f1"], s["strict_precision"]) == (None, None, None, None)


def test_all_wrong_gives_zero_f1():
    s = score(BATCH, ["e02"])
    assert (s["precision"], s["recall"], s["f1"]) == (0.0, 0.0, 0.0)


def test_f1_handles_zero_and_none():
    assert f1_score(0.0, 0.0) == 0.0
    assert f1_score(None, 1.0) is None
    assert f1_score(0.5, 1.0) == pytest.approx(2 / 3)


def test_score_rejects_unknown_ids():
    with pytest.raises(ValueError, match="e99"):
        score(BATCH, ["e99"])


def test_fmt():
    assert fmt(None) == "n/a"
    assert fmt(2 / 3) == "0.67"


# ---------- prompt and dataset ----------


def test_build_prompt_fills_emails_like_a_real_run():
    prompt = build_prompt("Urgent ones: {{ n1.output.payload.emails }}", BATCH[:2])
    assert prompt == "Urgent ones: " + json.dumps(["Server is down!", "Lunch on Friday?"])


def test_build_prompt_needs_the_placeholder():
    with pytest.raises(ValueError, match="n1.output.payload.emails"):
        build_prompt("List the urgent emails.", BATCH)


def test_build_prompt_with_only_the_placeholder_is_text():
    assert build_prompt("{{n1.output.payload.emails}}", BATCH[:1]) == '["Server is down!"]'


def test_default_config_is_the_example_llm_step():
    config = load_default_config()
    assert "{{n1.output.payload.emails}}" in config["prompt"]
    assert config["output_schema"] == {"urgent": "list[str]"}


def test_batches():
    items = [{"id": str(i)} for i in range(25)]
    assert [len(b) for b in batches(items, 10)] == [10, 10, 5]


def test_validate_dataset_rejects_texts_that_only_differ_in_case():
    with pytest.raises(ValueError, match="same text"):
        validate_dataset(
            [
                {"id": "e01", "text": "Server down", "urgent": True},
                {"id": "e02", "text": " server DOWN ", "urgent": True},
            ]
        )


def test_validate_dataset_rejects_duplicate_ids_and_bad_labels():
    with pytest.raises(ValueError, match="duplicate id"):
        validate_dataset([{"id": "e01", "text": "a", "urgent": True}, {"id": "e01", "text": "b", "urgent": False}])
    with pytest.raises(ValueError, match="true or false"):
        validate_dataset([{"id": "e01", "text": "a", "urgent": "yes"}])


def test_shipped_dataset_is_valid():
    # Only checks the file is well formed, so changing the labels never breaks the tests.
    assert load_dataset(DEFAULT_DATASET)


def test_default_seed_mixes_every_batch_of_the_shipped_dataset():
    args = parse_args([])
    groups = batches(shuffled(load_dataset(DEFAULT_DATASET), args.seed), args.batch_size)
    for i, batch in enumerate(groups, start=1):
        labels = {e["urgent"] for e in batch}
        assert labels == {True, False}, f"batch {i} is not mixed: {[e['id'] for e in batch]}"
