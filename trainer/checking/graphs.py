"""Course datasets loaded into rdflib graphs (cached), plus small helpers for showing RDF terms."""
import threading

import owlrl
from rdflib import Graph, Literal

from trainer import config

_cache = {}
_lock = threading.Lock()

SHORT_NS = [
    ("https://example.org/bivak/kategorie/", "kat:"),
    ("https://example.org/bivak/iucn/", "iucn:"),
    ("https://example.org/bivak/typ-op/", "optyp:"),
    ("https://example.org/bivak#", ":"),
    ("https://kbss.fel.cvut.cz/bivak#", "bv:"),
    ("http://www.w3.org/2000/01/rdf-schema#", "rdfs:"),
    ("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:"),
    ("http://www.w3.org/2004/02/skos/core#", "skos:"),
]


def fresh():
    """Empty graph without implicit prefixes: like GraphDB, a query must declare its PREFIXes."""
    return Graph(bind_namespaces="none")


def copy_into(dst, src):
    for t in src:
        dst.add(t)
    return dst


def rdfs_closure(g):
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)
    return g


def base_graph(names, infer):
    """The named datasets merged into one graph, optionally with RDFS inference ("Include inferred")."""
    key = (tuple(names), infer)
    with _lock:
        if key not in _cache:
            raw = Graph()
            for n in names:
                raw.parse(str(config.DATASETS[n]))
            g = copy_into(fresh(), raw)
            if infer == "rdfs":
                rdfs_closure(g)
            _cache[key] = g
        return _cache[key]


def term(x):
    if x is None:
        return ""
    if isinstance(x, Literal) and x.language:
        return f"{x}@{x.language}"
    return str(x)


def short(s):
    """Replace well-known namespaces by their prefixes (only for display)."""
    for ns, p in SHORT_NS:
        s = s.replace(ns, p)
    return s
