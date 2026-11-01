# OSW Trainer

An interactive trainer for the semantic-web part of the **B4M36OSW** course: Turtle, SPARQL, RDFS/SKOS and RML.
Every task is checked on real data — your query is run next to the reference query and the results are compared.

- **78 tasks** in 4 sections: 28 lessons with theory and hints → SPARQL practice → RDF practice → an exam without hints
- answers checked locally: SPARQL (rdflib, with optional RDFS inference as GraphDB's *Include inferred*), Turtle (ASK checks), RML (Morph-KGC)
- explanations of errors: undeclared prefixes, Cyrillic look-alike letters, wrong namespace IRIs, missing / extra rows
- side panel with copyable prefixes and an index of the dataset (classes, properties, individuals, SKOS vocabularies)
- **Russian and English** built in; **any other language** can be added with an AI model (see below)
- dark theme by default, light theme one click away
- progress and drafts are kept in the browser

## Quick start

You need **Python 3.10+** and internet for the first start (dependencies are installed into `.venv/` inside the folder).

| System | Command |
|---|---|
| macOS / Linux | `./start.sh` |
| Windows | `py start.py` (or `python start.py`) |

The browser opens at <http://127.0.0.1:8765/>. Stop with `Ctrl+C`. Later starts are instant.

Options: `--port 8800`, `--no-browser`, `--no-rml` (skip Morph-KGC, ~100 MB; only the 6 RML tasks need it),
`--reinstall` (recreate `.venv/`), `--selftest` (check every reference answer and exit).

## Adding a language

1. In the language list (top left) choose **＋ Another language…**
2. Enter the target language (e.g. `Deutsch`, code `de`), choose the source language and download the template (`.arb`).
3. Press **Copy prompt**, paste it into an AI chat and attach the template.
4. Upload the translated file. The language appears in the list immediately.

The whole template is ~220 KB. If the model cuts its answer short, download and translate it **part by part**
(interface, then each section); uploaded parts are merged into one language. Untranslated strings fall back to the source language.

Uploads are validated: placeholders such as `{got}` must survive, HTML is cleaned to a short allow-list
(so a pack received from someone else cannot run scripts), and built-in languages cannot be overwritten.
Uploaded languages are stored in `locales/custom/` (not committed). To ship a language with the trainer,
move its file to `locales/`.

### Why ARB

[ARB](https://github.com/google/app-resource-bundle) is plain JSON where every string `key` may have an `@key` entry with a
description, its format in `context` (`html`, `code`, or plain text when absent) and its placeholders. That context is exactly what an AI model needs to
translate HTML lessons without breaking code samples.

## Project layout

The code is organised by feature; content is data, not code.

```
start.sh / start.py        one-command launch (creates .venv, installs requirements, starts the server)
content/lessons.json       structure of every task: kind, datasets, reference answer, checks, starter code
locales/en.arb             English texts + "@key" metadata (the translation template)
locales/ru.arb             Russian texts
data/                      course datasets (bivak, ZCHÚ SKOS/RDFS, four-thousanders) and the RML sample CSV
trainer/
  i18n/                    ARB catalogs, fallback chain, template export, pack import + HTML sanitizer
  lessons/                 lessons in a given language; "data names you will need"
  checking/                one checker per task kind: sparql.py, turtle.py, rml.py (+ error diagnostics)
  schema/                  index of the data for the side panel
  server/                  local HTTP server: static UI + JSON API (localhost only)
  cli.py                   command line (--port, --no-browser, --selftest)
web/
  index.html, css/app.css  page shell and theme tokens (dark by default)
  js/core/                 api, i18n, store, actions, shared state
  js/features/             lessons, editor, sidebar, languages, theme, progress
tests/                     unittest suite
```

No build step: the browser loads the ES modules directly; the server uses only the Python standard library plus rdflib/owlrl.

## Development

```sh
./start.sh --selftest                              # every reference answer passes its own checks
.venv/bin/python -m unittest discover -s tests     # unit + integration tests (Windows: .venv\Scripts\python)
.venv/bin/python -m trainer --port 8800            # run without the launcher
```

**Adding a task:** append an entry to `content/lessons.json` (new `id`), add its texts to `locales/en.arb`
(with `@lesson_<id>_…` metadata) and `locales/ru.arb`, then run the selftest and the tests.

API (all on `127.0.0.1`; writes require the `X-Trainer: 1` header):
`GET /api/lessons?lang=`, `GET /api/i18n?lang=`, `GET /api/schema`, `GET /api/solution?id=`, `POST /api/run`,
`GET /api/locales`, `GET /api/locales/template?source=&part=&code=&name=`, `POST /api/locales`, `DELETE /api/locales/<code>`.
