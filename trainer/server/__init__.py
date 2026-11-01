"""Feature: the local web server — static UI under / and a small JSON API under /api/."""
import functools
import json
import mimetypes
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from trainer import checking, config, lessons, schema
from trainer.i18n import Catalogs, PackRejected

catalogs = Catalogs()
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
LOCALE_PATH = re.compile(r"^/api/locales/([A-Za-z0-9-]+)$")


def _guarded(method):
    """Turn an unexpected exception into a JSON 500 instead of a dropped connection."""
    @functools.wraps(method)
    def wrapper(self):
        try:
            method(self)
        except Exception as e:
            traceback.print_exc()
            self._json(dict(error=f"{type(e).__name__}: {e}"), 500)
    return wrapper


class Handler(BaseHTTPRequestHandler):
    server_version = "OSWTrainer"

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------------- plumbing
    def _send(self, code, body, ctype="application/json", headers=()):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text/", "application/j")) else ""))
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def _json(self, data, code=200, headers=()):
        self._send(code, json.dumps(data, ensure_ascii=False), headers=headers)

    def _query(self):
        q = parse_qs(urlparse(self.path).query)
        return lambda k, d="": q.get(k, [d])[0]

    def _local_host(self):
        """Reject requests whose Host is not this machine (DNS-rebinding protection)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host in LOCAL_HOSTS:
            return True
        self._json(dict(error="forbidden host"), 403)
        return False

    def _same_origin_write(self):
        """Writes need a custom header, which other web sites cannot send to localhost without a CORS preflight."""
        if self.headers.get("X-Trainer") == "1":
            return True
        self._json(dict(error="missing X-Trainer header"), 403)
        return False

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    # ---------------------------------------------------------------- routes
    @_guarded
    def do_GET(self):
        if not self._local_host():
            return
        path, q = urlparse(self.path).path, self._query()
        if path == "/api/locales":
            return self._json(catalogs.locales())
        if path == "/api/i18n":
            return self._json(catalogs.client_strings(q("lang", "ru")))
        if path == "/api/lessons":
            t = catalogs.translator(q("lang", "ru"))
            return self._json(dict(tabs=lessons.tabs(), lessons=[lessons.localize(t, l) for l in lessons.all_lessons()]))
        if path == "/api/schema":
            return self._json(schema.payload())
        if path == "/api/solution":
            l = lessons.by_id().get(int(q("id", "0") or 0))
            return self._json(dict(ref=l["ref"])) if l else self._json({}, 404)
        if path == "/api/locales/template":
            return self._template(q)
        return self._static(path)

    @_guarded
    def do_POST(self):
        if not (self._local_host() and self._same_origin_write()):
            return
        path, q = urlparse(self.path).path, self._query()
        if path == "/api/run":
            body = json.loads(self._body() or b"{}")
            l = lessons.by_id().get(int(body.get("id", 0)))
            if not l:
                return self._json({}, 404)
            t = catalogs.translator(body.get("lang", "ru"))
            try:
                res = checking.check(t, l, body.get("text", ""), bool(body.get("infer")))
            except Exception as e:
                res = dict(error=f"{type(e).__name__}: {e}")
            return self._json(res)
        if path == "/api/locales":
            t = catalogs.translator(q("lang", "ru"))
            try:
                rep = catalogs.import_pack(self._body().decode("utf-8-sig", errors="replace"), q("code"), q("name"))
            except PackRejected as e:
                return self._json(dict(error=t(e.key, **e.params)), 400)
            rep["warnings"] = [t(k, **p) for k, p in rep["warnings"]]
            return self._json(rep)
        return self._json({}, 404)

    @_guarded
    def do_DELETE(self):
        if not (self._local_host() and self._same_origin_write()):
            return
        m = LOCALE_PATH.match(urlparse(self.path).path)
        if m and catalogs.remove(m.group(1)):
            return self._json(dict(ok=True))
        return self._json(dict(error=catalogs.translator(self._query()("lang", "ru"))("imp_notFound")), 404)

    def _template(self, q):
        part = q("part", "all")
        if part not in {"all", "ui"} | {t["id"] for t in lessons.tabs()}:
            return self._json({}, 400)
        code, name = q("code").strip(), q("name").strip()
        if code and not re.match(r"^[A-Za-z0-9-]{1,20}$", code):
            code = ""
        arb = catalogs.export_template(q("source", config.TEMPLATE_LOCALE), lessons.template_filter(part), code, name)
        fname = f"osw-trainer.{code or 'xx'}.{part}.arb"
        return self._send(200, json.dumps(arb, ensure_ascii=False, indent=2) + "\n", "application/json", headers=[
            ("Content-Disposition", f"attachment; filename=\"{fname}\"; filename*=UTF-8''{quote(fname)}")])

    def _static(self, path):
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        f = (config.WEB_DIR / rel).resolve()
        if config.WEB_DIR.resolve() not in f.parents or not f.is_file():
            return self._json({}, 404)
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix == ".js":
            ctype = "text/javascript"  # some Windows registries map .js to text/plain, which breaks ES modules
        return self._send(200, f.read_bytes(), ctype)


def serve(port):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
