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

import json
import re
from typing import Any

from app.errors import TemplateError

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\s*\}\}")


def lookup(path: str, context: dict[str, Any]) -> Any:
    current = context
    keys = path.split(".")

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise TemplateError(f"unknown reference: {path}")
        current = current[key]

    return current


# Assumed defined elsewhere in your file:
# PLACEHOLDER = re.compile(r'\${([^}]+)}')


def render(value: Any, context: dict[str, Any]) -> Any:
    # 1. String Processing
    if isinstance(value, str):
        # Rule 1: Full-string placeholder returns the raw matched object type
        m = PLACEHOLDER.fullmatch(value)
        if m:
            return lookup(m.group(1), context)

            # Rule 2: placeholders inside text

        def replacer(match: re.Match) -> str:
            found = lookup(match.group(1), context)
            if isinstance(found, str):
                return found
            return json.dumps(found)

        return PLACEHOLDER.sub(replacer, value)

        # 2. Dictionary Processing
    if isinstance(value, dict):
        return {k: render(v, context) for k, v in value.items()}

    # 3. List Processing
    if isinstance(value, list):
        return [render(v, context) for v in value]

    # 4. Rules 3-6 / Fallback

    return value
