# Repository Inventory

This inventory records the tracked repository surface reviewed during
maintenance. It avoids checked-in line counts because those drift after ordinary
patches. Generate fresh counts from the worktree when you need them.

## Audit Commands

List tracked files:

```bash
jj file list
```

Count tracked lines:

```bash
jj file list | xargs wc -l | tail -1
```

Check local documentation links:

```bash
python - <<'PY'
from pathlib import Path
import re

root = Path(".")
missing = []
for path in root.rglob("*.md"):
    if any(part in {".venv", ".git", ".jj", "dist"} for part in path.parts):
        continue
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
        if "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            missing.append((path, target))

if missing:
    for path, target in missing:
        print(f"{path}: missing {target}")
    raise SystemExit(1)
PY
```

## Root And Project Metadata

| File | Role |
| --- | --- |
| `.env.example` | Blank local environment variable template. |
| `.gitignore` | Local ignore rules. |
| `.python-version` | Python version pin. |
| `AGENTS.md` | Harness-agnostic coding-agent instructions. |
| `CHANGELOG.md` | User-facing release notes. |
| `CLAUDE.md` | Claude-specific project context. |
| `CODEOWNERS` | Repository ownership. |
| `CODE_OF_CONDUCT.md` | Collaboration expectations. |
| `CONTRIBUTING.md` | Contributor workflow notes. |
| `LICENSE` | MIT license. |
| `README.md` | Short product overview and docs entry point. |
| `SECURITY.md` | Vulnerability reporting policy. |
| `SUPPORT.md` | Support and reproduction guidance. |
| `package.json` | npm launcher package metadata. |
| `pyproject.toml` | Python package, dependency, build, test, and lint metadata. |
| `uv.lock` | Locked Python dependency graph. |

## GitHub Metadata

| File | Role |
| --- | --- |
| `.github/assets/traccia-logo.svg` | Repository logo used in the README. |
| `.github/assets/traccia-loop-squircle.gif` | README viewer animation. |
| `.github/dependabot.yml` | Dependency update configuration. |
| `.github/pull_request_template.md` | Pull request checklist. |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Bug report form. |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Feature request form. |
| `.github/workflows/ci.yml` | CI workflow. |
| `.github/workflows/release.yml` | Release workflow. |
| `.github/workflows/security.yml` | Security workflow. |

## User And Maintainer Docs

| Path | Role |
| --- | --- |
| `docs/index.md` | Documentation index. |
| `docs/quickstart.md` | First-run tutorial. |
| `docs/cli-reference.md` | Command reference. |
| `docs/project-layout.md` | Generated project layout reference. |
| `docs/configuration.md` | Config schema guide. |
| `docs/ingestion.md` | Ingest, staging, scoring, and source-family guide. |
| `docs/exports.md` | Markdown, Obsidian, viewer, admin, and publish guide. |
| `docs/architecture.md` | System model and boundaries. |
| `docs/codebase-map.md` | Repository maintainer map. |
| `docs/development.md` | Local development and packaging guide. |
| `docs/repository-inventory.md` | This repository surface inventory. |
| `docs/spec.md` | Product specification. |
| `docs/architecture-notes.md` | Implementation notes. |
| `docs/ingest-architecture.md` | Detailed ingest architecture. |
| `docs/finished-run-viewer-decisions.md` | Viewer decisions. |
| `docs/plan.md` | Original phased implementation plan. |
| `docs/decisions.md` | Planning decisions. |
| `docs/references.md` | External references and anti-references. |

## Product Code And Tests

The product code lives under `src/traccia/`. Tests live under `tests/`, with
fixtures under `tests/fixtures/`. The package also tracks the npm launcher under
`npm/` and maintainer scripts under `scripts/`.

Generated caches, local virtual environments, `dist/`, `tmp/`, local runner
scripts, private font source assets, and local ingest outputs are intentionally
outside the tracked product surface.
