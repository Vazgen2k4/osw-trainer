#!/usr/bin/env python3
"""One-command start on any OS:   python start.py   (Windows: py start.py;  macOS/Linux: ./start.sh)

First run: creates .venv/ next to this file and installs the dependencies into it (needs internet once).
Later runs: start immediately; dependencies are reinstalled only when requirements*.txt change.

Options (everything else is passed to the trainer, e.g. --port 8800, --no-browser, --selftest):
  --no-rml     skip Morph-KGC (large; only the 6 RML lessons need it)
  --reinstall  recreate .venv from scratch
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
CORE = ROOT / "requirements.txt"
RML = ROOT / "requirements-rml.txt"
STAMP = VENV / ".installed"


def say(msg):
    print(f"[osw-trainer] {msg}", flush=True)


def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def digest(files):
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def create_venv():
    say(f"creating a virtual environment in {VENV.name}/ …")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    except subprocess.CalledProcessError:
        shutil.rmtree(VENV, ignore_errors=True)
        sys.exit("Could not create the virtual environment. On Debian/Ubuntu install it first: "
                 "sudo apt install python3-venv")


def pip_install(req):
    cmd = [str(venv_python()), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(req)]
    return subprocess.run(cmd).returncode == 0


def ensure_dependencies(with_rml):
    wanted = [CORE] + ([RML] if with_rml else [])
    if STAMP.exists() and STAMP.read_text().strip() == digest(wanted):
        return
    say("installing dependencies (first start only, needs internet) …")
    if not pip_install(CORE):
        sys.exit("Installing the dependencies failed — check the internet connection and run start again.")
    if with_rml:
        say("installing Morph-KGC for the RML lessons (the largest part, ~1–2 min) …")
        if not pip_install(RML):
            say("WARNING: Morph-KGC could not be installed; everything works except checking RML lessons. "
                "Retry later with --reinstall.")
            return  # no stamp: the next start tries again
    STAMP.write_text(digest(wanted))
    say("dependencies installed.")


def main():
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %d.%d+ is required (this is %s). Download: https://www.python.org/downloads/"
                 % (*MIN_PYTHON, sys.version.split()[0]))
    args = sys.argv[1:]
    with_rml = "--no-rml" not in args
    if "--reinstall" in args and VENV.exists():
        say("removing the old .venv/ …")
        shutil.rmtree(VENV)
    args = [a for a in args if a not in ("--no-rml", "--reinstall")]
    if not venv_python().exists():
        create_venv()
    ensure_dependencies(with_rml)
    os.chdir(ROOT)
    try:
        sys.exit(subprocess.call([str(venv_python()), "-m", "trainer", *args]))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
