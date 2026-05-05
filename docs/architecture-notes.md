# architecture notes

This document captures implementation-level decisions that are easy to lose in code review.

## persistence

SQLite is the canonical derived state. Markdown, JSON, the static viewer, Obsidian exports, and profile files are projections over `state/catalog.sqlite`.

The schema is initialized from static SQL in `bootstrap.py` and incrementally checked in `storage.py`. SQLite cannot bind table or column identifiers, so any dynamic identifier formatting must validate identifiers first.

## extraction boundary

First-pass extraction is source-scoped. The extractor sees one parsed source or one chunk of a large source, plus that source's local metadata and linked attachment context. It must not use a corpus-wide summary as the evidence boundary.

The durable extraction output is an `EvidenceItem` with:

| field group | purpose |
| --- | --- |
| source and span | ties a claim back to one source and exact offsets |
| quote and time reference | preserves the inspectable evidence trail |
| evidence type and signal class | separates direct work from weak or ambient traces |
| reliability and confidence | lets scoring reduce weak signals without discarding them |

## scoring

The current deterministic support score is:

```text
support = evidence_type_weight * signal_class_multiplier * confidence
```

High-signal actions are implementation, debugging, design, review, teaching, and presenting when the signal class is artifact-backed work or problem-solving trace. Community teaching, presenting, and review can count as strong action. Passive evidence such as mentions, self-claims, studying, and ambient interest is allowed to support awareness but cannot independently imply deep implementation skill.

The default consumption-only cap is level 2. This is a product safety rule, not just a heuristic: reading, watching, liking, following, or talking about a topic should not become a high-level skill without stronger action evidence.

## freshness

Freshness is stepwise in v1:

| latest evidence age | recency score | freshness |
| --- | --- | --- |
| 0-90 days | `1.0` | `active` |
| 91-180 days | `0.7` | `warming` |
| 181-365 days | `0.4` | `stale` |
| older | `0.15` | `historical` |

This is intentionally simple until there is a golden corpus for calibration.

## graph refresh

Large directory ingests checkpoint every material, but rendered graph refreshes can be batched. Batching changes when projections update; it does not merge multiple materials into one lossy LLM prompt.

Every accepted evidence item is stored separately before graph recompute. Final graph sync recomputes from the complete evidence table.

## contribution risk areas

The highest-risk modules are:

| module | reason |
| --- | --- |
| `pipeline.py` | orchestrates discovery, extraction, resumability, graph recompute, review, and rendering |
| `pipeline_support.py` | contains support scoring and level caps |
| `storage.py` | owns SQLite persistence and additive schema checks |
| `llm.py` | owns structured backend calls, retry behavior, and prompt-injection boundary text |
| `parsers.py` / `family_normalizer.py` | encode messy source-family and export-shape assumptions |
| `rendering.py` | turns canonical graph state into user-facing artifacts |

Changes to these modules should include tests that exercise observable behavior rather than only implementation details.
