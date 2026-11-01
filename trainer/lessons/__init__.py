"""Feature: lessons — structure from content/lessons.json, texts from the language catalogs."""
import functools
import json
import re

from trainer import config
from trainer import schema


@functools.lru_cache(maxsize=1)
def content():
    return json.loads(config.CONTENT_FILE.read_text(encoding="utf-8"))


def all_lessons():
    return content()["lessons"]


@functools.lru_cache(maxsize=1)
def by_id():
    return {l["id"]: l for l in all_lessons()}


def tabs():
    return content()["tabs"]


def _items(t, prefix, n):
    """Indexed strings prefix_0 … prefix_{n-1}; an item missing in every catalog is skipped."""
    return [(k, v) for k in range(n) for v in [t.get(f"{prefix}_{k}")] if v]


def localize(t, l):
    """A lesson as the browser needs it, in the translator's language. Reference answers are not included."""
    p = f"lesson_{l['id']}"
    d = {k: l[k] for k in ("id", "tab", "kind", "infer", "exam")}
    d.update(part=t(f"part_{l['part']}"), title=t(f"{p}_title"), theory=t.get(f"{p}_theory", ""),
             key=t.get(f"{p}_key", ""), task=t.get(f"{p}_task", ""), starter=t.get(f"{p}_starter", l["starter"]))
    # the original English wording of the task, as it will appear on the test (pointless in English itself)
    d["taskOriginal"] = l.get("taskOriginal", "") if t.code != "en" else ""
    d["hints"] = [v for _, v in _items(t, f"{p}_hint", l.get("hints", 0))]
    notes = l.get("notes", [])
    d["notes"] = [[t(f"note_{notes[k]}"), v] for k, v in _items(t, f"{p}_note", len(notes))]
    d["terms"] = [[term, t.get(f"{p}_term_{k}", "")] for k, term in enumerate(l.get("terms", []))]
    d["origins"] = [[o[0], o[1], t.get(f"{p}_origin_{k}", "")] for k, o in enumerate(l.get("origins", []))]
    d["needs"] = needs(t, l)
    return d


_NAME = re.compile(r"(?<![\w:<\"/#])((?:kat|iucn|optyp)?:[A-Za-z_][\w-]*)")


def needs(t, l):
    """Names from the data that the reference answer uses, with a one-line meaning each (not for the exam)."""
    if l["kind"] != "sparql" or l["exam"]:
        return []
    S = schema.index()
    ref = re.sub(r"PREFIX[^\n]*\n", "", l["ref"])
    names = list(dict.fromkeys(m.group(1) for m in _NAME.finditer(ref)))
    out = []
    for n in names:
        if n in S["classes"]:
            c = S["classes"][n]
            kind = t("needs_class")
            out.append([n, t("needs_subclassOf", kind=kind, parents=", ".join(c["parents"])) if c["parents"] else kind, c["label"]])
        elif n in S["props"]:
            p = S["props"][n]
            kind, dom, rng = t("needs_property"), ", ".join(p["domain"]), ", ".join(p["range"])
            if dom and rng:
                text = t("needs_domainRange", kind=kind, domain=dom, range=rng)
            elif rng:
                text = t("needs_rangeOnly", kind=kind, range=rng)
            elif dom:
                text = t("needs_domainOnly", kind=kind, domain=dom)
            else:
                text = kind
            out.append([n, t("needs_transitive", text=text) if p["transitive"] else text, p["label"]])
        elif n in S["inst"]:
            i = S["inst"][n]
            out.append([n, t("needs_individual", types=", ".join(i["types"])), i["label"]])
        elif n in S["concepts"]:
            c = S["concepts"][n]
            kind = t("needs_concept")
            out.append([n, t("needs_notation", kind=kind, notation=c["notation"]) if c["notation"] else kind, c["label"]])
    return out


def template_filter(part):
    """Which catalog keys belong to a part of the translation template: 'all', 'ui' or a tab id."""
    if part == "all":
        return lambda k: True
    if part == "ui":
        return lambda k: not k.startswith(("lesson_", "part_"))
    ids = {str(l["id"]) for l in all_lessons() if l["tab"] == part}
    return lambda k: (k.startswith("part_" + part) or
                      (k.startswith("lesson_") and k.split("_", 2)[1] in ids))
