"""Feature: checking answers. One checker per task kind; all of them speak through a Translator."""
from trainer.checking import rml, sparql, turtle


def check(t, lesson, text, infer=False):
    kind = lesson["kind"]
    if kind == "sparql":
        return sparql.check(t, lesson, text, infer)
    if kind == "turtle":
        return turtle.check(t, lesson, text)
    return rml.check(t, lesson, text)


__all__ = ["check"]
