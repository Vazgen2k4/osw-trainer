"""SPARQL tasks: run the learner's query and the reference query on the same data and compare."""
from collections import Counter

from trainer.checking.diagnostics import query_error
from trainer.checking.graphs import base_graph, short, term


def run_query(g, q):
    res = g.query(q)
    if res.type == "SELECT":
        return dict(type="SELECT", cols=[str(v) for v in res.vars], rows=[[term(x) for x in r] for r in res])
    if res.type == "ASK":
        return dict(type="ASK", value=bool(res.askAnswer))
    if res.type == "CONSTRUCT":
        return dict(type="CONSTRUCT", triples=sorted((term(s), term(p), term(o)) for s, p, o in res))
    return dict(type=res.type)


def _diff(t, missing, extra, sep):
    return [t("msg_missing", item=short(sep.join(r))) for r in missing[:6]] + \
           [t("msg_extra", item=short(sep.join(r))) for r in extra[:6]]


def compare(t, user, ref, ordered):
    """Return (passed, message, diff lines)."""
    if user["type"] != ref["type"]:
        return False, t("msg_wrongType", expected=ref["type"], actual=user["type"]), []
    if ref["type"] == "ASK":
        ok = user["value"] == ref["value"]
        return ok, t("msg_correct") if ok else t("msg_askWrong", got=user["value"], expected=ref["value"]), []
    if ref["type"] == "CONSTRUCT":
        u, r = set(user["triples"]), set(ref["triples"])
        if u == r:
            return True, t("msg_correct"), []
        return (False, t("msg_graphDiffers", got=len(u), expected=len(r)),
                _diff(t, sorted(r - u), sorted(u - r), " "))
    ucols, rcols = user["cols"], ref["cols"]
    ur, rr = [tuple(r) for r in user["rows"]], [tuple(r) for r in ref["rows"]]
    cols = ", ".join("?" + c for c in rcols)
    if len(ucols) != len(rcols):
        return False, t("msg_columnCount", got=len(ucols), expected=len(rcols), cols=cols), []
    if (ur == rr) if ordered else (sorted(ur) == sorted(rr)):
        if ucols != rcols:
            return True, t("msg_columnNames", cols=cols), []
        return True, t("msg_correct"), []
    cu, cr = Counter(ur), Counter(rr)
    missing, extra = list(cr - cu), list(cu - cr)
    if not missing and not extra and ordered:
        return False, t("msg_orderDiffers"), []
    return False, t("msg_rowCount", got=len(ur), expected=len(rr)), _diff(t, missing, extra, " | ")


def check(t, lesson, text, infer_flag):
    want = lesson["infer"]
    if want == "rdfs" and not infer_flag:
        try:
            u = run_query(base_graph(lesson["data"], "none"), text)
        except Exception as e:
            return dict(error=query_error(t, e, text))
        return dict(result=u, passed=False, message=t("msg_needInferred"), diff=[])
    try:
        u = run_query(base_graph(lesson["data"], want if want == "rdfs" else ("rdfs" if infer_flag else "none")), text)
    except Exception as e:
        return dict(error=query_error(t, e, text))
    ref = run_query(base_graph(lesson["data"], want), lesson["ref"])
    ordered = lesson["ordered"] and "order by" in lesson["ref"].lower()
    ok, msg, diff = compare(t, u, ref, ordered)
    return dict(result=u, passed=ok, message=msg, diff=diff)
