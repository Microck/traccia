<div align="center">
  <img src=".github/assets/traccia-logo.svg" alt="traccia logo" width="220">
  <h1>traccia</h1>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-000000?style=flat-square" alt="python badge">
  <img src="https://img.shields.io/badge/license-MIT-000000?style=flat-square" alt="mit license badge">
</p>

<p align="center">
  <img width="800" height="auto" alt="traccia exported skill map animation" src=".github/assets/traccia-loop-squircle.gif" />
</p>

`traccia` turns personal archives into an evidence-backed skill graph.

feed it notes, code, documents, exports, chats, and the usual pile of
half-structured personal history. it keeps the source files untouched, extracts
evidence one source at a time, and renders a graph that shows what skills
appear, how strong the evidence is, how fresh the skill looks, and why the claim
exists.

it is built for reflection, not resume scoring. weak signals stay weak, raw
files stay private by default, and published views are generated through an
explicit curation step.

## quick start

install the Python CLI from a checkout:

```bash
uv sync
uv tool install -e .
```

create a project and ingest a folder:

```bash
traccia init my-traccia
traccia doctor my-traccia
traccia ingest-dir /path/to/archive --project-root my-traccia
traccia tree --project-root my-traccia
traccia explain python --project-root my-traccia
```

export the results:

```bash
traccia export obsidian --project-root my-traccia
traccia export viewer --project-root my-traccia
traccia export admin --project-root my-traccia
traccia export publish --project-root my-traccia
```

## what it produces

| output | purpose |
| --- | --- |
| `graph/graph.json` | Machine-readable skill graph. |
| `tree/index.md` | Markdown overview of the graph. |
| `tree/nodes/*.md` | One markdown page per skill. |
| `profile/skill.md` | A profile summary derived from accepted graph state. |
| `exports/obsidian/` | Obsidian-friendly vault export. |
| `exports/viewer/` | Public read-only skill map viewer. |
| `exports/viewer-admin/` | Admin curation viewer. |
| `exports/viewer-public/` | Redacted public bundle generated from curation. |

## install paths

the canonical implementation is the Python package. the npm package is a thin
launcher for Node-first environments.

| path | command | notes |
| --- | --- | --- |
| repo-local | `uv sync` then `uv run traccia ...` | best while developing. |
| editable CLI | `uv tool install -e .` | installs `traccia` on `PATH`. |
| pip editable | `pip install -e .` | same console script through pip. |
| npm one-off | `npx @microck/traccia doctor .` | requires `uvx` on `PATH`. |
| npm global | `npm install -g @microck/traccia` | installs the npm launcher. |

optional document parsing extras are available when you need heavier local PDF
or DOCX normalization:

```bash
uv sync --extra docling
uv sync --extra marker
uv sync --extra document-markdown
```

## documentation

start here:

- [Documentation index](docs/index.md)
- [Quickstart](docs/quickstart.md)
- [CLI reference](docs/cli-reference.md)
- [Project layout](docs/project-layout.md)
- [Ingestion guide](docs/ingestion.md)
- [Configuration reference](docs/configuration.md)
- [Exports and publishing](docs/exports.md)
- [Architecture overview](docs/architecture.md)
- [Codebase map](docs/codebase-map.md)
- [Repository inventory](docs/repository-inventory.md)
- [Development guide](docs/development.md)

design records and deeper planning notes remain in `docs/` for maintainers.

## core guarantees

- Source files in `raw/` are not rewritten by the LLM.
- First-pass extraction is scoped to one source or source chunk.
- Evidence is stored before graph scoring.
- SQLite is the canonical derived state.
- Markdown, JSON, profile files, and viewers are projections.
- Public publishing physically removes hidden/private graph data from the public
  bundle.

## license

MIT
