# contributing

`traccia` is still early and optimizes for one clear current implementation over compatibility shims. Changes should keep the evidence-first contract intact: raw sources stay immutable, extraction is source-scoped, and graph output remains traceable back to stored evidence.

## local setup

```bash
uv sync --dev
uv run traccia --help
```

Use the Python CLI as the source of truth. The npm package is only a thin launcher around the Python package.

## verification

Run the same checks CI runs before opening or merging changes:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv build
npm pack --dry-run
```

If a change touches dependencies, run `uv lock` and include the lockfile update.

## code expectations

Keep changes small and directly tied to the issue being solved. Do not add compatibility bridges for old local states unless a task explicitly calls for that support. Prefer fail-fast diagnostics and documented recovery steps over silent fallback paths.

Tests should use real implementations, fixtures, or in-memory substitutes. Do not mock modules. When adding parsing or scoring behavior, include enough fixture coverage to prove source provenance, evidence type, confidence, and weak-signal behavior.

## data safety

Never commit personal archive outputs, local ingest runs, credentials, mounted-drive paths, or generated private graph artifacts. The repo ignores `tmp/`, `.env*`, caches, and local runner scripts for that reason.

Before pushing archive-ingest changes, scan the diff for personal paths, emails, API keys, bearer tokens, and provider credentials.
