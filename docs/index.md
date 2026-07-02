# Traccia Documentation

Traccia is a local-first CLI that compiles a personal archive into an
evidence-backed skill graph. The docs are split by reader task: start with the
quickstart, then use the reference pages when you need exact commands or file
contracts.

## Start Here

| Page | Use it when |
| --- | --- |
| [Quickstart](quickstart.md) | You want to create a project, ingest files, and inspect the first graph. |
| [CLI reference](cli-reference.md) | You need the exact command surface and common options. |
| [Project layout](project-layout.md) | You want to understand what a Traccia project stores. |
| [Ingestion guide](ingestion.md) | You are importing folders, archives, exports, or long-running datasets. |
| [Configuration reference](configuration.md) | You are changing backend, privacy, multimodal, or performance settings. |
| [Exports and publishing](exports.md) | You want markdown, Obsidian, graph JSON, or the public viewer. |
| [Architecture overview](architecture.md) | You want the system model and data flow. |
| [Codebase map](codebase-map.md) | You are maintaining the repository and need module ownership. |
| [Repository inventory](repository-inventory.md) | You want the tracked repository surface and audit commands. |
| [Development guide](development.md) | You want to run tests, package the CLI, or work on the repo. |

## Deeper Records

These files capture planning and design history. They are useful for maintainers
but are not the best entry point for a new user.

| File | Contents |
| --- | --- |
| [Spec](spec.md) | Product scope, goals, non-goals, input model, and output contracts. |
| [Architecture notes](architecture-notes.md) | Implementation decisions and high-risk modules. |
| [Ingest architecture](ingest-architecture.md) | Detailed ingest, staging, scoring, and source-family decisions. |
| [Viewer decisions](finished-run-viewer-decisions.md) | Public/admin viewer design decisions. |
| [Plan](plan.md) | Original phased implementation plan. |
| [Decisions](decisions.md) | Product and architecture decisions from planning. |
| [References](references.md) | External project references and anti-references. |
| [Changelog](../CHANGELOG.md) | User-facing release notes. |

## Mental Model

Traccia has three separate layers:

```text
raw files -> parsed spans -> evidence -> scored graph -> rendered exports
```

The raw archive is not the graph. The graph is a derived projection over stored
evidence, and exports are projections over the graph. This separation is the
main reason Traccia can explain why a skill exists and can publish a redacted
view without exposing private source material.
