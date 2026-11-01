"""RML tasks: run the learner's mapping and the reference mapping through Morph-KGC and compare the triples."""
import functools
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from rdflib import Graph

from trainer import config
from trainer.checking.graphs import short, term


@functools.lru_cache(maxsize=1)
def morph_python():
    """Interpreter that can run Morph-KGC: $MORPH_PY if set, otherwise the trainer's own one."""
    env = os.environ.get("MORPH_PY")
    if env and Path(env).exists():
        r = subprocess.run([env, "-c", "import morph_kgc"], capture_output=True)
        if r.returncode == 0:
            return env
    return sys.executable if importlib.util.find_spec("morph_kgc") else None


def _obj(o):
    dt = getattr(o, "datatype", None)
    return f"{o}^^{short(str(dt))}" if dt else term(o)


def triples(t, mapping_text):
    """Run one mapping on the sample CSV. Returns (set of triples, None) or (None, error message)."""
    py = morph_python()
    if not py:
        return None, t("msg_morphMissing")
    with tempfile.TemporaryDirectory() as w:
        w = Path(w)
        (w / "mapping.ttl").write_text(mapping_text, encoding="utf-8")
        (w / "mzchu-sample.csv").write_text(config.RML_CSV.read_text(encoding="utf-8"), encoding="utf-8")
        (w / "config.ini").write_text(config.RML_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run([py, "-m", "morph_kgc", "config.ini"], cwd=w, capture_output=True, text=True, timeout=120)
        out = w / "out.nt"
        if r.returncode != 0 or not out.exists():
            return None, t("msg_morphFailed", detail="\n".join((r.stdout + r.stderr).strip().splitlines()[-6:]))
        g = Graph().parse(str(out), format="nt")
        return {(term(s), term(p), _obj(o)) for s, p, o in g}, None


_ref_cache = {}


def check(t, lesson, text):
    try:
        Graph().parse(data=text, format="turtle")
    except Exception as e:
        return dict(error=t("msg_rmlTurtle", detail=e))
    user, err = triples(t, text)
    if err:
        return dict(error=err)
    ref = _ref_cache.get(lesson["id"])
    if ref is None:
        ref, err = triples(t, lesson["ref"])
        if err:
            return dict(error=err)
        _ref_cache[lesson["id"]] = ref
    shown = [dict(s=short(s), p=short(p), o=short(o)) for s, p, o in sorted(user)]
    if user == ref:
        return dict(passed=True, message=t("msg_rmlCorrect", count=len(user)), triples=shown, diff=[])
    diff = [t("msg_missing", item=short(" ".join(x))) for x in sorted(ref - user)[:6]] + \
           [t("msg_extra", item=short(" ".join(x))) for x in sorted(user - ref)[:6]]
    return dict(passed=False, message=t("msg_rmlCount", got=len(user), expected=len(ref)), triples=shown, diff=diff)
