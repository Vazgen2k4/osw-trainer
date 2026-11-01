"""Feature: the "Data" side panel — an index of classes, properties, individuals and SKOS concepts in the course data."""
import functools

from rdflib import BNode, Graph
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from trainer import config
from trainer.checking.graphs import SHORT_NS, short

SCHEME_PREFIX = {"kat:schema": "kat:", "iucn:schema": "iucn:", "optyp:schema": "optyp:"}


def sn(u):
    u = str(u)
    for ns, p in SHORT_NS[:4]:  # dataset namespaces first, so ":" wins over the generic replacements
        if u.startswith(ns):
            return p + u[len(ns):]
    return short(u)


def _label(g, s):
    for pred in (RDFS.label, SKOS.prefLabel):
        labels = list(g.objects(s, pred))
        for want in ("en", "cs", None):
            for x in labels:
                if want is None or getattr(x, "language", None) == want:
                    return str(x)
    return ""


def _literal(o):
    return '"%s"%s' % (o, ("@" + o.language) if o.language else "")


@functools.lru_cache(maxsize=1)
def index():
    """Everything named in bivak.ttl + the SKOS vocabularies, keyed by short name."""
    g = Graph()
    for n in ("bivak", "skos"):
        g.parse(str(config.DATASETS[n]))
    classes, props, inst, concepts = {}, {}, {}, {}
    for c in g.subjects(RDF.type, RDFS.Class):
        classes[sn(c)] = dict(name=sn(c), label=_label(g, c), parents=[sn(p) for p in g.objects(c, RDFS.subClassOf)])
    for p in g.subjects(RDF.type, RDF.Property):
        ex = next(((sn(s), _literal(o) if hasattr(o, "language") else sn(o))
                   for s, o in sorted(g.subject_objects(p), key=str) if not isinstance(s, BNode)), None)
        props[sn(p)] = dict(name=sn(p), label=_label(g, p), domain=[sn(x) for x in g.objects(p, RDFS.domain)],
                            range=[sn(x) for x in g.objects(p, RDFS.range)], example=ex,
                            transitive=(p, RDF.type, OWL.TransitiveProperty) in g)
    for s in set(g.subjects(RDF.type, None)):
        if isinstance(s, BNode):
            continue
        types = [sn(t) for t in g.objects(s, RDF.type)]
        if any(t in ("rdfs:Class", "rdf:Property") for t in types) or sn(s) in classes or sn(s) in props:
            continue
        if "skos:Concept" in types or "skos:ConceptScheme" in types:
            nt = next(iter(g.objects(s, SKOS.notation)), None)
            concepts[sn(s)] = dict(name=sn(s), label=_label(g, s), types=types, notation=str(nt) if nt else "")
        elif any(t.startswith(":") for t in types):
            inst[sn(s)] = dict(name=sn(s), label=_label(g, s), types=[t for t in types if t.startswith(":")])
    return dict(classes=classes, props=props, inst=inst, concepts=concepts)


@functools.lru_cache(maxsize=1)
def payload():
    S = index()
    kids = {}
    for c in S["classes"].values():
        for p in c["parents"] or [None]:
            kids.setdefault(p, []).append(c["name"])
    tree = []

    def walk(n, depth):
        tree.append(dict(name=n, label=S["classes"][n]["label"], depth=depth))
        for k in sorted(kids.get(n, [])):
            walk(k, depth + 1)

    for root in sorted(kids.get(None, [])):
        walk(root, 0)
    groups = {}
    for i in S["inst"].values():
        for t in i["types"]:
            groups.setdefault(t, []).append(i["name"])
    schemes = [dict(name=n, label=c["label"],
                    concepts=sorted(x["notation"] or x["name"] for x in S["concepts"].values()
                                    if x["name"].startswith(SCHEME_PREFIX.get(n, "§")) and not x["name"].endswith(":schema")))
               for n, c in sorted(S["concepts"].items()) if "skos:ConceptScheme" in c["types"]]
    return dict(tree=tree, props=sorted(S["props"].values(), key=lambda p: p["name"]),
                inst=[dict(cls=t, n=len(v), items=sorted(v)[:12]) for t, v in sorted(groups.items())],
                schemes=schemes)
