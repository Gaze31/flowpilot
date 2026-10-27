"""Errors raised by the service/engine layer and mapped to HTTP codes in main.py. Done."""


class NotFound(Exception):
    """-> 404"""


class CycleError(Exception):
    """The workflow graph has a loop, so there is no valid order to run it in. -> 422"""


class TemplateError(Exception):
    """A {{...}} reference points at something that doesn't exist. Fails the node."""
