"""Human-readable parser errors: where the error is and which characters are probably to blame."""
import re
import unicodedata

_MASK = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|#[^\n]*|<[^<>\s"]*>')


def hidden_chars(text):
    """Characters that look like ASCII (or are invisible) but are not: Cyrillic homoglyphs, NBSP, zero-width …
    Looked for outside string literals, comments and IRIs, where non-Latin text is perfectly fine."""
    masked = _MASK.sub(lambda m: " " * len(m.group(0)), text)
    out = []
    for ln, line in enumerate(masked.split("\n"), 1):
        for col, ch in enumerate(line, 1):
            if ord(ch) > 127:
                try:
                    nm = unicodedata.name(ch)
                except ValueError:
                    nm = "?"
                out.append((ln, col, ch, "U+%04X %s" % (ord(ch), nm)))
    return out


def where(t, message, text):
    """The offending line with a caret under the column, plus any suspicious characters."""
    s = ""
    loc = re.search(r"line:(\d+), col:(\d+)", message)
    if loc and text:
        ln, col = int(loc.group(1)), int(loc.group(2))
        lines = text.split("\n")
        if 1 <= ln <= len(lines):
            s += "\n" + lines[ln - 1] + "\n" + " " * (col - 1) + "^"
    hc = hidden_chars(text) if text else []
    if hc:
        s += "\n\n" + t("msg_suspicious") + "\n"
        s += "\n".join(t("msg_suspiciousAt", line=a, col=b, char=c if c.strip() else "·", name=d) for a, b, c, d in hc[:6])
        s += "\n" + t("msg_suspiciousFix")
    return s


def query_error(t, e, text=""):
    m = str(e)
    if "Unknown namespace prefix" in m:
        return t("msg_prefixUndeclared", detail=m) + where(t, m, text)
    return f"{type(e).__name__}: {m}" + where(t, m, text)


def turtle_error(t, e):
    """rdflib's Turtle messages contain raw byte dumps; turn them into one actionable sentence."""
    m = str(e)
    line = re.search(r"at line (\d+)", m)
    at = t("msg_atLine", line=line.group(1)) if line else ""
    pm = re.search(r'Prefix "([^"]*)" not bound', m)
    if pm:
        return t("msg_ttlPrefix", name=pm.group(1).rstrip(":"), where=at)
    if "Bad syntax" in m:
        what = re.search(r"Bad syntax \((.*?)\)", m)
        return t("msg_ttlSyntax", where=at, what=what.group(1) if what else t("msg_ttlSyntaxDefault"))
    return t("msg_ttlOther", where=at, detail=m.splitlines()[-1][:200])
