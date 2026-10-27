"""Fill {{node_id.output.field}} placeholders with earlier nodes' outputs. WEEK 2 TODO.

The context passed in looks like:
    {"n1": {"output": {"emails": ["Server down!", "Lunch?"], "count": 2}}}

Rules (the tests check each one):
  1. A string that is EXACTLY one placeholder returns the raw value, keeping its type:
         "{{n1.output.count}}"           -> 2              (an int, not "2")
         "{{n1.output.emails}}"          -> ["Server down!", "Lunch?"]
  2. A placeholder inside longer text is converted to text:
         "You have {{n1.output.count}} emails" -> "You have 2 emails"
     (lists/dicts become JSON text: json.dumps(value))
  3. dicts and lists are filled recursively, keys stay the same:
         {"to": "me", "body": "{{n1.output.count}}"} -> {"to": "me", "body": 2}
  4. Anything that isn't a str/dict/list (int, None, bool) is returned unchanged.
  5. A path that doesn't exist raises TemplateError("unknown reference: n9.output.x").
  6. Spaces inside braces are allowed: "{{ n1.output.count }}".
"""

import json  # noqa: F401
import re
from typing import Any

from app.errors import TemplateError  # noqa: F401

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\s*\}\}")


def lookup(path: str, context: dict[str, Any]) -> Any:
    """'n1.output.emails' -> context['n1']['output']['emails'].

    TODO (Week 2): split on '.', walk the dicts one key at a time.
    If a key is missing (or you hit something that isn't a dict), raise
    TemplateError(f"unknown reference: {path}").
    """
    raise NotImplementedError("lookup: see TODO in app/engine/templating.py")


def render(value: Any, context: dict[str, Any]) -> Any:
    """Apply rules 1-6 above.

    TODO (Week 2):
      - str:  m = PLACEHOLDER.fullmatch(value) -> rule 1.
              otherwise PLACEHOLDER.sub(replacer, value) -> rule 2
              (replacer gets a match; m.group(1) is the path).
      - dict: {k: render(v, context) for ...}
      - list: [render(v, context) for ...]
      - else: return value
    """
    raise NotImplementedError("render: see TODO in app/engine/templating.py")
