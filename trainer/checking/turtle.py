"""Turtle tasks: parse the learner's data and run the lesson's ASK checks against it."""
from rdflib import Graph

from trainer.checking.diagnostics import turtle_error
from trainer.checking.graphs import base_graph, copy_into, fresh, rdfs_closure


def _prefix_reason(t, graph, expected_ns):
    """Explain the most common failure: a prefix bound to a different namespace IRI than the task asks for."""
    mine = {p: str(n) for p, n in graph.namespaces()}
    out = ""
    for prefix, want in (expected_ns or {}).items():
        got = mine.get(prefix)
        if got is not None and got.startswith("file://"):
            got = got.rsplit("/", 1)[-1]  # a relative IRI was resolved against the working directory
        if got is not None and got != want:
            out += "\n" + t("msg_prefixReason", prefix=prefix, got=got, want=want)
    return out


def check(t, lesson, text):
    try:
        user = Graph(bind_namespaces="none").parse(data=text, format="turtle")
    except Exception as e:
        return dict(error=turtle_error(t, e))
    out = []
    for k, c in enumerate(lesson["checks"]):
        g = user
        if c.get("base"):
            g = copy_into(copy_into(fresh(), user), base_graph(lesson["data"], "none"))
        if c.get("infer") == "rdfs":
            g = rdfs_closure(copy_into(fresh(), g))
        desc = t(f"lesson_{lesson['id']}_check_{k}")
        try:
            ok = bool(g.query(c["q"]).askAnswer)
        except Exception as e:
            ok, desc = False, t("msg_checkError", desc=desc, detail=e)
        out.append(dict(desc=desc, ok=ok))
    passed = all(o["ok"] for o in out)
    msg = t("msg_allChecks") if passed else t("msg_notAllChecks") + _prefix_reason(t, user, lesson.get("ns"))
    return dict(passed=passed, checks=out, message=msg)
