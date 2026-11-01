import json
import shutil
import tempfile
import unittest
from pathlib import Path

from trainer import config, lessons
from trainer.i18n import Catalogs, PackRejected
from trainer.i18n.sanitize import sanitize


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for f in ("en.arb", "ru.arb"):
            shutil.copy(config.LOCALES_DIR / f, self.tmp / f)
        self.cat = Catalogs(self.tmp, self.tmp / "custom")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def upload(self, data, **kw):
        return self.cat.import_pack(json.dumps(data), **kw)

    def test_builtin_locales(self):
        codes = {x["code"]: x for x in self.cat.locales()}
        self.assertEqual(set(codes), {"en", "ru"})
        self.assertTrue(all(x["builtin"] and x["coverage"] == 100 for x in codes.values()))

    def test_placeholders_are_filled_and_braces_in_code_are_left_alone(self):
        t = self.cat.translator("en")
        self.assertEqual(t("msg_rowCount", got=2, expected=3), "You have 2 rows, expected 3.")
        self.assertEqual(t("imp_notString", key="x"), "Key x: the value must be a string — skipped.")
        self.assertIn("&#123;", t("lesson_6_theory"))  # literal braces in HTML are entities (valid ICU)
        self.assertIn("{KOD}", t("lesson_26_starter", other=1))  # undeclared params never touch code
        self.assertEqual(t("missing_key"), "missing_key")

    def test_unknown_language_falls_back_to_template(self):
        self.assertEqual(self.cat.translator("xx").code, "en")

    def test_upload_partial_pack_falls_back_to_source(self):
        rep = self.upload({"@@locale": "de", "@@x-name": "Deutsch", "@@x-source-locale": "en", "ui_menu": "Menü"})
        self.assertEqual((rep["code"], rep["name"], rep["count"]), ("de", "Deutsch", 1))
        t = self.cat.translator("de")
        self.assertEqual(t("ui_menu"), "Menü")
        self.assertEqual(t("ui_hint"), "Hint")

    def test_parts_are_merged(self):
        self.upload({"@@locale": "de", "ui_menu": "Menü"})
        self.upload({"@@locale": "de", "ui_hint": "Hinweis"})
        t = self.cat.translator("de")
        self.assertEqual((t("ui_menu"), t("ui_hint")), ("Menü", "Hinweis"))

    def test_locale_code_from_dialog_when_model_kept_the_source_code(self):
        rep = self.upload({"@@locale": "en", "@@x-source-locale": "en", "ui_menu": "Menü"}, fallback_code="de",
                          fallback_name="Deutsch")
        self.assertEqual((rep["code"], rep["name"]), ("de", "Deutsch"))

    def test_rejections(self):
        cases = [("not json", "imp_notJson"), ("[]", "imp_notObject"), (json.dumps({"ui_menu": "x"}), "imp_noLocale"),
                 (json.dumps({"@@locale": "../x", "ui_menu": "x"}), "imp_badLocale"),
                 (json.dumps({"@@locale": "ru", "ui_menu": "x"}), "imp_builtin"),
                 (json.dumps({"@@locale": "de", "nope": "x"}), "imp_empty")]
        for raw, key in cases:
            with self.subTest(key=key), self.assertRaises(PackRejected) as e:
                self.cat.import_pack(raw)
            self.assertEqual(e.exception.key, key)

    def test_broken_placeholder_is_dropped_with_warning(self):
        rep = self.upload({"@@locale": "de", "ui_menu": "Menü", "msg_rowCount": "Zeilen: {n}"})
        self.assertIn("imp_placeholders", [w[0] for w in rep["warnings"]])
        self.assertEqual(self.cat.translator("de")("msg_rowCount", got=1, expected=2), "You have 1 rows, expected 2.")

    def test_scripts_are_removed(self):
        rep = self.upload({"@@locale": "de", "ui_examBanner": '<b>x</b><script>alert(1)</script><img src=x onerror=alert(1)>'})
        self.assertIn("imp_sanitized", [w[0] for w in rep["warnings"]])
        self.assertEqual(self.cat.translator("de")("ui_examBanner"), "<b>x</b>")

    def test_code_and_text_are_stored_verbatim(self):
        starter = 'rml:template "https://kbss.fel.cvut.cz/bivak#MZCHU_{KOD}" ;\n# dein Mapping\n'
        rep = self.upload({"@@locale": "de", "lesson_26_starter": starter, "ui_menu": "a < b"})
        self.assertEqual(rep["warnings"], [])
        t = self.cat.translator("de")
        self.assertEqual((t("lesson_26_starter"), t("ui_menu")), (starter, "a < b"))

    def test_literal_braces_in_html_become_entities(self):
        self.upload({"@@locale": "de", "lesson_6_hint_0": "<code>WHERE { ?s ?p ?o }</code>"})
        self.assertEqual(self.cat.translator("de")("lesson_6_hint_0"), "<code>WHERE &#123; ?s ?p ?o &#125;</code>")

    def test_code_placeholders_must_survive(self):
        bad = self.cat._file("en")["lesson_26_starter"].replace("{KOD}", "{CODE}")
        rep = self.upload({"@@locale": "de", "ui_menu": "Menü", "lesson_26_starter": bad})
        self.assertIn("imp_placeholders", [w[0] for w in rep["warnings"]])

    def test_remove(self):
        self.upload({"@@locale": "de", "ui_menu": "Menü"})
        self.assertTrue(self.cat.remove("de"))
        self.assertFalse(self.cat.remove("de"))
        self.assertFalse(self.cat.remove("en"))

    def test_every_message_has_template_metadata(self):
        meta = self.cat.template_meta()
        for f in ("en.arb", "ru.arb"):
            keys = [k for k in json.loads((config.LOCALES_DIR / f).read_text(encoding="utf-8")) if not k.startswith("@")]
            self.assertEqual([k for k in keys if k not in meta], [], f)
        en = json.loads((config.LOCALES_DIR / "en.arb").read_text(encoding="utf-8"))
        self.assertEqual([k for k in meta if k not in en], [], "metadata without a message in the template")

    def test_template_parts_cover_every_key(self):
        meta = self.cat.template_meta()
        parts = ["ui"] + [t["id"] for t in lessons.tabs()]
        for key in meta:
            owners = [p for p in parts if lessons.template_filter(p)(key)]
            self.assertEqual(len(owners), 1, f"{key} belongs to {owners}")

    def test_exported_template_round_trips(self):
        tpl = self.cat.export_template("ru", lessons.template_filter("exam"), "uk", "Українська")
        self.assertEqual((tpl["@@locale"], tpl["@@x-source-locale"]), ("uk", "ru"))
        self.assertTrue(all(k.startswith(("@", "lesson_", "part_exam")) for k in tpl))
        rep = self.upload(tpl)
        self.assertEqual(rep["warnings"], [])


class SanitizeTest(unittest.TestCase):
    def test_builtin_html_needs_no_cleaning(self):
        """The allow-list covers every tag the lessons use, so a faithful translation is never altered."""
        meta = Catalogs().template_meta()
        for f in ("en.arb", "ru.arb"):
            for k, v in json.loads((config.LOCALES_DIR / f).read_text(encoding="utf-8")).items():
                if meta.get(k, {}).get("context") == "html":
                    with self.subTest(file=f, key=k):
                        self.assertFalse(sanitize(v)[1])

    def test_entities_and_code_are_kept(self):
        html = '<pre>SELECT ?s WHERE { ?s ?p &lt;x&gt; }</pre><span class="small" title="t">a &amp; b</span>'
        self.assertEqual(sanitize(html), (html, False))

    def test_attack_vectors(self):
        for bad in ('<a href="javascript:alert(1)">x</a>', '<svg onload=alert(1)>', '<p onclick="x()">x</p>',
                    '<iframe src="//evil"></iframe>', '<style>*{}</style>'):
            with self.subTest(bad=bad):
                out, changed = sanitize(bad)
                self.assertTrue(changed)
                self.assertNotRegex(out.lower(), r"<(a|svg|iframe|style)|on\w+=|javascript:")


if __name__ == "__main__":
    unittest.main()
