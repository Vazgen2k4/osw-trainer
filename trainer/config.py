"""Filesystem layout of the trainer. Everything is resolved relative to the project root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTENT_FILE = ROOT / "content" / "lessons.json"
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

LOCALES_DIR = ROOT / "locales"            # built-in languages, shipped with the repository
CUSTOM_LOCALES_DIR = LOCALES_DIR / "custom"  # languages uploaded by the user (git-ignored)
TEMPLATE_LOCALE = "en"                    # its .arb carries the "@key" metadata for every string

DATASETS = {
    "bivak": DATA_DIR / "bivak.ttl",
    "skos": DATA_DIR / "zchu-skos.ttl",
    "rdfs": DATA_DIR / "zchu-rdfs.ttl",
    "four": DATA_DIR / "four-thousanders.ttl",
}
RML_CSV = DATA_DIR / "rml" / "mzchu-sample.csv"
RML_CONFIG = DATA_DIR / "rml" / "config.ini"

DEFAULT_PORT = 8765
