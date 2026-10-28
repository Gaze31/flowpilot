"""Week 2: filling {{node.output.field}} templates."""

import pytest

from app.engine.templating import render
from app.errors import TemplateError

CTX = {"n1": {"output": {"emails": ["Server down!", "Lunch?"], "count": 2, "meta": {"from": "boss"}}}}


def test_whole_string_keeps_type():
    assert render("{{n1.output.count}}", CTX) == 2
    assert render("{{n1.output.emails}}", CTX) == ["Server down!", "Lunch?"]


def test_inside_text_becomes_text():
    assert render("You have {{n1.output.count}} emails", CTX) == "You have 2 emails"
    assert render("List: {{n1.output.emails}}", CTX) == 'List: ["Server down!", "Lunch?"]'


def test_nested_dicts_and_lists():
    assert render({"to": "me", "body": "{{n1.output.count}}", "tags": ["{{n1.output.meta.from}}"]}, CTX) == {
        "to": "me",
        "body": 2,
        "tags": ["boss"],
    }


def test_non_strings_unchanged():
    assert render(5, CTX) == 5
    assert render(None, CTX) is None
    assert render("no templates here", CTX) == "no templates here"


def test_spaces_inside_braces():
    assert render("{{ n1.output.count }}", CTX) == 2


def test_unknown_reference_raises():
    with pytest.raises(TemplateError):
        render("{{n9.output.x}}", CTX)
    with pytest.raises(TemplateError):
        render("{{n1.output.missing}}", CTX)
