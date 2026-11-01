import unittest

from trainer import checking, lessons
from trainer.checking import rml
from trainer.i18n import Catalogs


class ContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = Catalogs()

    def test_ids_are_unique(self):
        ids = [l["id"] for l in lessons.all_lessons()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_lesson_is_complete_in_builtin_languages(self):
        for code in ("ru", "en"):
            t = self.cat.translator(code)
            for l in lessons.all_lessons():
                with self.subTest(lang=code, id=l["id"]):
                    d = lessons.localize(t, l)
                    self.assertNotEqual(d["title"], f"lesson_{l['id']}_title")
                    self.assertTrue(d["task"])
                    self.assertNotIn("ref", d)  # solutions are fetched separately
                    if l["kind"] == "turtle":
                        self.assertTrue(all(t.get(f"lesson_{l['id']}_check_{k}") for k in range(len(l["checks"]))))

    def test_original_task_wording_is_hidden_in_english(self):
        l = lessons.by_id()[1]
        self.assertTrue(lessons.localize(self.cat.translator("ru"), l)["taskOriginal"])
        self.assertEqual(lessons.localize(self.cat.translator("en"), l)["taskOriginal"], "")


class ReferenceAnswersTest(unittest.TestCase):
    """Every reference answer must pass its own checks (the same as `python -m trainer --selftest`)."""

    def test_reference_answers_pass(self):
        t = Catalogs().translator("en")
        for l in lessons.all_lessons():
            if l["kind"] == "rml" and not rml.morph_python():
                continue
            with self.subTest(id=l["id"], kind=l["kind"]):
                r = checking.check(t, l, l["ref"], l["infer"] == "rdfs")
                self.assertTrue(r.get("passed"), r.get("error") or r.get("message"))

    def test_wrong_answer_is_explained(self):
        t = Catalogs().translator("en")
        l = lessons.by_id()[6]
        r = checking.check(t, l, "SELECT ?p WHERE { ?s ?p ?o }", False)
        self.assertFalse(r["passed"])
        self.assertIn("columns", r["message"])
        r = checking.check(t, l, "SELECT ?p ?o WHERE { :SpotB ?p ?o }", False)
        self.assertIn("PREFIX", r["error"])


if __name__ == "__main__":
    unittest.main()
