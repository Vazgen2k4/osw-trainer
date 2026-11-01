"""Command line: start the server (default) or check that every reference answer passes its own checks."""
import argparse
import sys
import threading
import webbrowser

from trainer import __version__, config


def selftest(lang="ru"):
    from trainer import checking, lessons
    from trainer.server import catalogs
    t = catalogs.translator(lang)
    bad = 0
    for l in lessons.all_lessons():
        r = checking.check(t, l, l["ref"], l["infer"] == "rdfs")
        ok = r.get("passed") is True
        if ok and l["kind"] == "sparql":
            res = r["result"]
            if not (res.get("rows") or res.get("triples") or res["type"] == "ASK"):
                ok, r["message"] = False, "reference answer returns an empty result"
        print(f"{'OK  ' if ok else 'FAIL'} #{l['id']:2d} [{l['kind']}] {t('lesson_%d_title' % l['id'])}"
              + ("" if ok else f"  -> {r.get('error') or r.get('message')} {r.get('diff') or r.get('checks') or ''}"))
        bad += not ok
    print("failures:", bad)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trainer", description="OSW trainer — RDF, SPARQL, RDFS/SKOS, RML")
    ap.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser")
    ap.add_argument("--selftest", action="store_true", help="check every reference answer and exit")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # a Windows console redirected to a file may not be UTF-8
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    if a.selftest:
        sys.exit(1 if selftest() else 0)

    from trainer.server import serve
    try:
        srv = serve(a.port)
    except OSError:
        sys.exit(f"Port {a.port} is busy — is the trainer already running? Try --port {a.port + 1}.")
    url = f"http://127.0.0.1:{a.port}/"
    print(f"OSW trainer {__version__}: {url}   (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        srv.server_close()
