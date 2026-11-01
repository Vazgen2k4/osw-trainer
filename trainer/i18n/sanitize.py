"""Allow-list HTML sanitizer for uploaded translations.

Lesson texts are HTML and are rendered with innerHTML, so a language pack received from someone else
(or produced by an AI model) must not be able to inject scripts. Only the handful of tags the lessons
actually use survive; entity references (&lt; …) are kept verbatim so code samples stay intact.
"""
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "b", "i", "em", "strong", "code", "pre", "mark", "div", "span", "small", "br", "h4",
                "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th", "sub", "sup", "kbd"}
VOID_TAGS = {"br"}
ALLOWED_ATTRS = {"class", "title"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out = []
        self.changed = False
        self._skip = 0  # depth inside <script>/<style>, whose text is dropped as well

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            self.changed = True
            return
        if tag not in ALLOWED_TAGS:
            self.changed = True
            return
        kept = [(k, v) for k, v in attrs if k in ALLOWED_ATTRS and v is not None]
        if len(kept) != len(attrs):
            self.changed = True
        self.out.append("<" + tag + "".join(f' {k}="{escape(v, quote=True)}"' for k, v in kept) + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.out.append(f"</{tag}>")
        elif tag not in ALLOWED_TAGS:
            self.changed = True

    def handle_data(self, data):
        if not self._skip:
            self.out.append(escape(data, quote=False))

    def handle_entityref(self, name):
        if not self._skip:
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if not self._skip:
            self.out.append(f"&#{name};")

    def handle_comment(self, data):
        self.changed = True


def sanitize(html):
    """Return (clean_html, changed)."""
    p = _Sanitizer()
    p.feed(html)
    p.close()
    return "".join(p.out), p.changed
