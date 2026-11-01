import json
import threading
import unittest
import urllib.error
import urllib.request

from trainer.server import serve


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve(0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def req(self, path, method="GET", body=None, headers=None):
        r = urllib.request.Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(r) as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_page_and_modules_are_served(self):
        code, h, body = self.req("/")
        self.assertEqual(code, 200)
        self.assertIn(b'type="module"', body)
        code, h, _ = self.req("/js/main.js")
        self.assertEqual((code, h["Content-Type"].split(";")[0]), (200, "text/javascript"))

    def test_files_outside_web_are_not_served(self):
        for p in ("/../trainer/config.py", "/%2e%2e/trainer/config.py", "/css/../../start.py"):
            self.assertEqual(self.req(p)[0], 404, p)

    def test_lessons_in_both_languages(self):
        for lang in ("ru", "en"):
            data = json.loads(self.req(f"/api/lessons?lang={lang}")[2])
            self.assertEqual(len(data["lessons"]), 78)

    def test_foreign_host_is_rejected(self):
        self.assertEqual(self.req("/api/locales", headers={"Host": "evil.example"})[0], 403)

    def test_writes_need_the_custom_header(self):
        body = json.dumps({"id": 6, "text": "ASK {}"}).encode()
        self.assertEqual(self.req("/api/run", "POST", body)[0], 403)
        code, _, out = self.req("/api/run", "POST", body, {"X-Trainer": "1"})
        self.assertEqual(code, 200)
        self.assertIn("passed", json.loads(out))

    def test_template_download(self):
        code, h, body = self.req("/api/locales/template?source=en&part=ui&code=de&name=Deutsch")
        self.assertEqual(code, 200)
        self.assertIn("attachment", h["Content-Disposition"])
        self.assertEqual(json.loads(body)["@@locale"], "de")
        self.assertEqual(self.req("/api/locales/template?part=../../x")[0], 400)


if __name__ == "__main__":
    unittest.main()
