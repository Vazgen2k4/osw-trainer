"""Translation catalogs stored as ARB files (Application Resource Bundle: JSON with "@key" metadata).

* ``locales/*.arb``         built-in languages. ``en.arb`` is the template: its "@key" entries describe every string.
* ``locales/custom/*.arb``  languages uploaded from the UI.

A locale that names a source language (``@@x-source-locale``) falls back to it, then to the template,
for any string it does not translate — so a partial translation is still usable.
"""
import json
import re
import threading
from datetime import datetime, timezone

from trainer import config
from trainer.i18n.sanitize import sanitize

LOCALE_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_]\w*)\}")
CLIENT_PREFIXES = ("ui_", "note_", "vocab_", "prefix_")  # strings the browser needs; the rest is rendered server-side


def is_message(key):
    return not key.startswith("@")


class PackRejected(Exception):
    """An uploaded language pack was rejected; ``args`` are (message key, params)."""

    def __init__(self, key, **params):
        super().__init__(key, params)
        self.key, self.params = key, params


class Translator:
    """Looks a key up along a fallback chain of catalogs and fills in declared placeholders."""

    def __init__(self, code, chain, placeholders):
        self.code = code
        self._chain = chain
        self._ph = placeholders

    def get(self, key, default=None):
        for cat in self._chain:
            v = cat.get(key)
            if v:
                return v
        return default

    def __call__(self, key, /, **params):  # positional-only: "key" is also a placeholder name
        text = self.get(key, key)
        names = self._ph.get(key)
        if not names or not params:
            return text
        # only declared placeholders are replaced: lesson HTML is full of SPARQL braces
        return PLACEHOLDER_RE.sub(lambda m: str(params[m.group(1)]) if m.group(1) in names and m.group(1) in params
                                  else m.group(0), text)


class Catalogs:
    def __init__(self, builtin_dir=config.LOCALES_DIR, custom_dir=config.CUSTOM_LOCALES_DIR,
                 template=config.TEMPLATE_LOCALE):
        self.builtin_dir, self.custom_dir, self.template = builtin_dir, custom_dir, template
        self._lock = threading.Lock()
        self._cache = {}  # path -> (mtime, data)

    # ---------------------------------------------------------------- loading
    def _read(self, path):
        mtime = path.stat().st_mtime
        hit = self._cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        data = json.loads(path.read_text(encoding="utf-8"))
        self._cache[path] = (mtime, data)
        return data

    def _path(self, code):
        for d, builtin in ((self.builtin_dir, True), (self.custom_dir, False)):
            p = d / f"{code}.arb"
            if p.is_file():
                return p, builtin
        return None, False

    def _file(self, code):
        p, _ = self._path(code)
        return self._read(p) if p else None

    def template_meta(self):
        """{key: metadata} for every known string (from the template's "@key" entries)."""
        t = self._file(self.template) or {}
        return {k[1:]: v for k, v in t.items() if k.startswith("@") and not k.startswith("@@")}

    def placeholders(self):
        return {k: set(m.get("placeholders", {})) for k, m in self.template_meta().items()}

    def exists(self, code):
        return bool(code) and bool(LOCALE_RE.match(code)) and self._path(code)[0] is not None

    def resolve(self, code):
        return code if self.exists(code) else self.template

    def chain(self, code):
        code = self.resolve(code)
        f = self._file(code)
        codes = [code]
        src = f.get("@@x-source-locale")
        if src:  # partial translations fall back to their source language, then to the template
            codes += [src, self.template]
        seen, out = set(), []
        for c in codes:
            if c not in seen and self.exists(c):
                seen.add(c)
                out.append({k: v for k, v in self._file(c).items() if is_message(k)})
        return code, out

    def translator(self, code):
        with self._lock:
            code, chain = self.chain(code)
            return Translator(code, chain, self.placeholders())

    def client_strings(self, code):
        t = self.translator(code)
        keys = [k for k in self.template_meta() if k.startswith(CLIENT_PREFIXES)]
        return dict(locale=t.code, strings={k: t.get(k, "") for k in keys})

    def locales(self):
        known = set(self.template_meta())
        out = []
        for d, builtin in ((self.builtin_dir, True), (self.custom_dir, False)):
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.arb")):
                code = p.stem
                if not LOCALE_RE.match(code) or (not builtin and (self.builtin_dir / p.name).exists()):
                    continue
                f = self._read(p)
                have = sum(1 for k, v in f.items() if k in known and isinstance(v, str) and v)
                src = f.get("@@x-source-locale")
                total = sum(1 for k, v in (self._file(src) or {}).items() if k in known and v) if src else have
                out.append(dict(code=code, name=f.get("@@x-name") or code, builtin=builtin,
                                coverage=round(100 * have / total) if total else 100))
        return out

    # ---------------------------------------------------------------- export
    def export_template(self, source, keys_filter, code="", name=""):
        """ARB file with the source texts and the metadata an AI model needs to translate them."""
        source = self.resolve(source)
        src = self._file(source)
        meta = self.template_meta()
        out = {"@@locale": code, "@@x-name": name, "@@x-source-locale": source,
               "@@last_modified": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        ctx = (self._file(self.template) or {}).get("@@context")
        if ctx:
            out["@@context"] = ctx
        for k in sorted(meta):
            v = src.get(k)
            if v and keys_filter(k):
                out[k] = v
                out["@" + k] = meta[k]
        return out

    # ---------------------------------------------------------------- import
    def import_pack(self, raw, fallback_code="", fallback_name=""):
        """Validate, sanitize and merge an uploaded ARB. Returns a report; raises PackRejected on rejection."""
        if len(raw) > MAX_UPLOAD_BYTES:
            raise PackRejected("imp_tooLarge", mb=MAX_UPLOAD_BYTES // (1024 * 1024))
        try:
            data = json.loads(raw)
        except ValueError as e:
            raise PackRejected("imp_notJson", detail=str(e)) from None
        if not isinstance(data, dict):
            raise PackRejected("imp_notObject")
        source = data.get("@@x-source-locale") if isinstance(data.get("@@x-source-locale"), str) else ""
        code = data.get("@@locale") if isinstance(data.get("@@locale"), str) else ""
        code = code.strip()
        if not code or code == source:  # the model kept the source code: use what the user typed in the dialog
            code = fallback_code.strip()
        if not code:
            raise PackRejected("imp_noLocale")
        if not LOCALE_RE.match(code):
            raise PackRejected("imp_badLocale", code=code)
        if (self.builtin_dir / f"{code}.arb").exists():
            raise PackRejected("imp_builtin", code=code)
        if not self.exists(source):
            source = self.template
        name = data.get("@@x-name") if isinstance(data.get("@@x-name"), str) and data.get("@@x-name").strip() else ""
        name = name.strip() if name and name != (self._file(source) or {}).get("@@x-name") else ""

        meta = self.template_meta()
        src = self._file(source)
        warnings, unknown, accepted = [], [], {}
        for k, v in data.items():
            if k.startswith("@"):
                continue
            if k not in meta:
                unknown.append(k)
                continue
            if not isinstance(v, str):
                warnings.append(("imp_notString", dict(key=k)))
                continue
            if not v.strip():
                continue
            want = set(meta[k].get("placeholders", {}))
            if want and set(PLACEHOLDER_RE.findall(v)) & want != want:
                warnings.append(("imp_placeholders", dict(key=k, expected=", ".join("{%s}" % n for n in sorted(want)))))
                continue
            # only HTML strings reach innerHTML; text and code are always escaped by the UI and must stay verbatim
            if meta[k].get("context") == "html":
                v, changed = sanitize(v)
                if changed:
                    warnings.append(("imp_sanitized", dict(key=k)))
                v = v.replace("{", "&#123;").replace("}", "&#125;")  # literal braces would read as ICU placeholders
                if src.get(k) and any(v.count(tag) != src[k].count(tag) for tag in ("<code", "<pre")):
                    warnings.append(("imp_markup", dict(key=k)))
            accepted[k] = v
        if unknown:
            warnings.insert(0, ("imp_unknown", dict(count=len(unknown), example=unknown[0])))
        if not accepted:
            raise PackRejected("imp_empty")

        with self._lock:
            self.custom_dir.mkdir(parents=True, exist_ok=True)
            path = self.custom_dir / f"{code}.arb"
            old = self._read(path) if path.exists() else {}
            merged = {"@@locale": code, "@@x-name": name or old.get("@@x-name") or fallback_name.strip() or code,
                      "@@x-source-locale": source,
                      "@@x-template": f"../{self.template}.arb",  # lets ARB editors find the metadata
                      "@@last_modified": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
            merged.update({k: v for k, v in old.items() if is_message(k)})
            merged.update(accepted)  # parts uploaded one by one are merged into the same file
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(path)
            self._cache.pop(path, None)
        info = next(x for x in self.locales() if x["code"] == code)
        return dict(code=code, name=info["name"], count=len(accepted), coverage=info["coverage"], warnings=warnings)

    def remove(self, code):
        if not LOCALE_RE.match(code or ""):
            return False
        p = self.custom_dir / f"{code}.arb"
        if not p.is_file():
            return False
        with self._lock:
            p.unlink()
            self._cache.pop(p, None)
        return True
