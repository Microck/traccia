# Agent Instructions

These instructions apply to coding agents working in this repository.

## Project Shape

Traccia is a local-first Python CLI with a thin npm launcher. The Python package
is the canonical implementation. The npm package only runs the Python CLI
through `uvx`, or through the local checkout when `TRACCIA_USE_LOCAL_REPO=1`.

Keep the core product contract intact:

- Raw source files are not rewritten by the LLM.
- First-pass extraction is scoped to one source or source chunk.
- Evidence is stored before graph scoring.
- SQLite is the canonical derived state.
- Markdown, JSON, profile files, and viewers are projections.
- Public publishing removes hidden and private graph data from the public bundle.

## Local Setup

Use `uv` for Python work:

```bash
uv sync --dev
uv run traccia --help
```

Use `npm` only for the launcher package checks. Do not introduce another
package manager unless the repository changes its lockfiles.

## Verification

Run the relevant subset while developing, and run the full set before handing
off a broad change:

```bash
uv run ruff check src tests
uv run pytest -q
uv build
uvx twine check --strict dist/*
npm pack --dry-run
```

If a change touches dependencies, run `uv lock` and include the lockfile update.
Keep repository-wide formatting changes in their own mechanical patch unless the
current task is specifically a formatting cleanup.

## Code Expectations

Prefer small, direct changes over new abstractions. Do not add compatibility
bridges for old local project states unless a task explicitly calls for that
support. Prefer fail-fast diagnostics and documented recovery steps over silent
fallback paths.

Tests should use real implementations, fixtures, or in-memory substitutes. Do
not mock modules. When adding parsing, scoring, export, or persistence behavior,
cover source provenance, evidence type, confidence, and weak-signal handling.

## Documentation

Keep the README compact and direct. It should explain what Traccia does, how to
start, where outputs land, and where deeper docs live. Put maintainer detail in
`docs/` instead of expanding the README.

When a change affects CLI behavior, config, generated artifacts, persistence
format, export redaction, packaging, or release workflow, update the matching
docs in the same patch.

## Data Safety

Never commit personal archives, ingest outputs, private graph artifacts,
credentials, mounted-drive paths, API keys, bearer tokens, or local `.env`
files. `.env.example` is the only environment file intended for version control.

Before publishing or pushing archive-ingest changes, inspect the diff for
personal paths, emails, credentials, and provider-specific tokens.
