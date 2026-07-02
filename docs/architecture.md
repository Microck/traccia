# Architecture Overview

Traccia is a pipeline over local files. It keeps raw inputs, evidence, graph
state, and rendered outputs separate so the system can explain each skill claim
and publish selectively.

## Data Flow

```text
source files
  -> discovery and source-family detection
  -> raw import
  -> parsing and span storage
  -> evidence extraction
  -> canonical skill matching
  -> person-skill scoring
  -> graph rendering
  -> markdown, profile, Obsidian, viewer, and public publish exports
```

## Boundaries

| Boundary | Rule |
| --- | --- |
| Raw input | The LLM never rewrites files in `raw/`. |
| Extraction | First-pass extraction sees one source or source chunk. |
| Evidence | Evidence records are durable and tied to source IDs and spans. |
| Graph | Scoring reads stored evidence and writes canonical graph state. |
| Rendering | Markdown, JSON, profile, and viewers are projections. |
| Publishing | Public bundles are separate redacted contracts, not lightly filtered admin data. |

## Evidence Model

Each evidence item stores:

- Source ID and span offsets.
- Exact supporting quote.
- Evidence type, such as implemented, debugged, studied, or self-claimed.
- Signal class, such as artifact-backed work or ambient interest.
- Candidate skills and artifacts.
- Time reference.
- Reliability tier.
- Extractor version and confidence.

This makes weak signals usable without allowing them to inflate mastery.

## Scoring Model

The current support score is:

```text
support = evidence_type_weight * signal_class_multiplier * confidence
```

High-signal actions include implementation, debugging, design, review,
teaching, and presenting when they are backed by artifact or problem-solving
evidence. Passive signals such as mentions, self-claims, and studying can show
awareness but cannot independently imply deep competence.

Consumption-led evidence is capped at level 2 by default.

## Freshness

Freshness is currently stepwise:

| Latest evidence age | Recency score | Freshness |
| --- | --- | --- |
| 0-90 days | `1.0` | `active` |
| 91-180 days | `0.7` | `warming` |
| 181-365 days | `0.4` | `stale` |
| Older | `0.15` | `historical` |

## Review And Overrides

Human curation is stored separately from automatic extraction and scoring.

Overrides can:

- Accept or reject review items.
- Lock skills.
- Hide skills.
- Add aliases.
- Apply viewer curation before publishing.

Manual state is part of the graph state and survives rendering.

## Failure And Resume Model

Ingest progress, manifests, extraction checkpoints, scoring progress, and run
telemetry are written under `state/`. Re-running an interrupted ingest should
resume from durable records rather than starting from zero.

The pipeline deliberately separates extraction from graph scoring. This allows
staged ingest, `--score-mode none`, and later scoring from stored evidence.
