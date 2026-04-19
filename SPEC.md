# SPEC.md

## 1. Product summary

`traccia` is a local-first CLI, markdown export set, and minimal local graph browser that ingests a person's data files one by one and builds a videogame-style skill tree of what they know, what they can do, what they have built, and how confident the system is in each conclusion.

The system is not a resume parser and not a generic personal wiki, though it can borrow from both. It is primarily a reflective self-profile archive whose main maintained artifact is a living skill graph for one real person, grounded in evidence from their files.

Primary artifact:
- a tree of skills, topics, tools, methods, and capabilities
- each node has a current inferred mastery level, confidence, freshness, evidence trail, and identity-centrality summary
- prerequisite and parent-child relationships make the graph navigable like a game skill tree

Secondary artifacts:
- a cited profile set derived from the graph
- Obsidian-friendly markdown exports for browsing outside the CLI

## 2. Goals

1. Build a personal skill tree from heterogeneous files.
2. Process sources incrementally, one file at a time.
3. Keep raw source material immutable.
4. Preserve exact provenance for every skill claim.
5. Distinguish observed evidence from inferred conclusions.
6. Let a human review, override, or lock parts of the graph.
7. Support local/private operation.
8. Produce both human-readable markdown and machine-readable graph output.
9. Preserve enough run history and provenance to understand how the archive changed over time.

## 3. Non-goals

1. Perfectly measuring competence.
2. Acting as an employee surveillance system.
3. Replacing interviews, mentorship, or formal assessment.
4. Performing broad personality analysis.
5. Publishing any private content by default.
6. Auto-generating prerequisites with no evidence or taxonomy support.
7. Resume optimization, job-fit scoring, or recruiter-first workflows.
8. A unified whole-person ontology in MVP.

## 4. Design principles

### 4.1 Evidence first
No skill should exist without at least one evidence item or an explicit human-added override.

### 4.2 Incremental by default
A new file should update only the affected parts of the graph.

### 4.3 Raw is immutable
Files in `raw/` are never rewritten by the LLM.

### 4.4 Separate fact from inference
The system stores:
- evidence: what the file directly supports
- claim: what the system infers
- assessment: current estimate of mastery/state

### 4.5 Human-overridable
Users can mark skills as:
- confirmed
- disputed
- hidden
- manually curated
- locked from future automatic edits

### 4.6 Stable IDs
Skill nodes, source documents, and evidence records use stable IDs so re-runs do not thrash the graph.

### 4.7 Local-first
The default deployment is local CLI + local database + optional local model or API model.

### 4.8 File-scoped first-pass synthesis
Extraction is performed file by file. The first synthesis pass for a file must use only that file and its local metadata, not wider corpus context.

### 4.9 Skill graph first
The broader archive may contain more than explicit skill signals, but MVP remains centered on the skill graph as the primary projection and decision surface.

### 4.10 Reflective archive, not job tool
Profile outputs are meant to help the subject inspect, remember, and communicate their own work and growth. External sharing is downstream and selective.

## 5. Users and use cases

### 5.1 Primary user
A single person building a persistent reflective archive of their real skills from their own files.

### 5.2 Secondary users
- mentors or coaches helping someone map strengths and gaps
- trusted collaborators reviewing exported profiles with explicit permission from the subject
- internal learning systems, if used with privacy controls and only as downstream consumers

### 5.3 Canonical use cases
1. Ingest a folder of notes, code, docs, and exports into a personal skill graph.
2. Ask "Why does the tree think I know Rust?"
3. See stale or decaying skills based on lack of recent evidence.
4. See dependencies and adjacent skills for growth planning.
5. Export a cited reflective profile for self-review, selective sharing, or archival recall.
6. Merge a new project repo and watch relevant nodes level up.
7. Review low-confidence skill claims before accepting them.
8. Ingest platform exports such as Reddit, Google, Twitter/X, AI chats, and profile exports without letting weak signals inflate mastery.

## 6. Input model

The system should support file-by-file ingestion through parsers and source adapters.
Per-file extraction is a hard contract, not just a performance optimization.

### 6.1 First-class source types
- Markdown notes
- Plain text
- PDF
- DOCX
- code files and git logs
- JSON / CSV exports
- calendar exports
- chat exports
- AI conversation exports
- social media profile exports
- Reddit, Twitter/X, YouTube, or forum data exports
- browser/search/activity exports
- bookmarks / reading lists
- issue trackers or task exports
- portfolio artifacts
- slide decks
- images only if a vision model is available

### 6.2 Source categories
- authored content
- consumed content
- platform-export activity
- social or community trace
- AI dialogue
- execution traces
- collaboration traces
- produced artifacts
- metadata-only activity

### 6.3 Source reliability tiers
Every source gets a reliability tier, for example:
- Tier A: code committed, shipped artifacts, authored docs, presentations delivered
- Tier B: detailed notes, design docs, project plans, calendar events with outcomes
- Tier C: bookmarks, saved links, light mentions, chat snippets
- Tier D: inferred-only or imported summaries

Reliability affects confidence, not whether a skill is allowed.

### 6.4 Archive breadth and weak-signal discipline
The system may ingest "everything" from a person's digital archive, but not every source should behave like direct proof of skill.

Examples of weak or ambient signals:
- search history
- bookmarks
- follows, likes, and reposts
- short comments
- profile bios
- AI chats with no demonstrated output

Examples of stronger signals:
- shipped artifacts
- code and design files
- authored long-form docs
- issue trackers with concrete execution
- detailed posts, tutorials, talks, and reviews

Weak signals may support interest, exposure, or identity context. They must not independently push a skill beyond awareness-level states.

### 6.5 Archive boundary in MVP
MVP may ingest broader personal material than explicit skill artifacts, but non-skill context is modeled only as auxiliary metadata or facets attached to sources and evidence. It does not become first-class scored graph nodes in MVP.

## 7. Output artifacts

Required outputs:
- `tree/index.md` - summary of the whole tree
- `tree/log.md` - append-only ingestion log
- `tree/nodes/<skill-id>.md` - one page per skill node
- `graph/graph.json` - canonical graph export
- `graph/tree.json` - layout-ready tree export
- `state/catalog.sqlite` - system state
- `state/review_queue.jsonl` - pending human review items
- `viewer/` - generated read-only local graph browser bundle

Secondary outputs:
- `profile/skill.md` - synthesized top-level profile
- `profile/strengths.md`
- `profile/gaps.md`
- `profile/artifacts.md`
- Obsidian-friendly markdown vault export

Each rendered node page should answer:
- where this skill fits
- when it first appeared
- when it was first strongly demonstrated
- how current it is
- what it connects to
- how deep the demonstrated competence is
- how central it is to the person's overall identity or recurring practice

## 8. Core conceptual model

The graph has four layers:

1. Canonical skill graph
- skills
- domains
- tools
- methods
- artifact types
- prerequisite edges
- parent-child edges
- related edges

2. Evidence layer
- evidence records
- source-category and reliability
- exact spans and timestamps
- direct action versus ambient signal distinction

3. Person skill overlay
- person-specific mastery estimates
- recency
- confidence
- level progress
- hidden/locked/manual flags

4. Identity overlay
- core-self centrality
- long-term recurrence
- periods of peak practice
- communities of practice
- self-claim versus demonstrated-self comparison

This separation keeps taxonomy cleaner than mixing person-state into the ontology itself.
Non-skill archive context may exist as auxiliary source, evidence, or identity facets, but it does not use the same scored mastery model in MVP.

## 9. Entity types

### 9.1 SourceDocument
Represents an ingested file or external item.

Fields:
- `source_id`
- `uri`
- `source_type`
- `parser`
- `sha256`
- `created_at`
- `ingested_at`
- `title`
- `language`
- `sensitivity`
- `metadata`
- `status`

### 9.2 EvidenceItem
A grounded observation tied to exact source spans.

Fields:
- `evidence_id`
- `source_id`
- `span_start`
- `span_end`
- `quote`
- `evidence_type`
- `skill_candidates`
- `artifact_candidates`
- `time_reference`
- `reliability`
- `extractor_version`

### 9.3 SkillNode
Represents a skill, topic, tool, method, or capability.

Fields:
- `skill_id`
- `kind` (`domain`, `skill`, `subskill`, `tool`, `method`, `topic`, `artifact`)
- `name`
- `slug`
- `aliases`
- `description`
- `taxonomy_refs`
- `status`
- `created_by`
- `last_updated`

### 9.4 SkillEdge
Graph relationship.

Fields:
- `edge_id`
- `from_skill_id`
- `to_skill_id`
- `edge_type`
- `weight`
- `source`
- `confidence`

Supported edge types:
- `parent_of`
- `part_of`
- `prerequisite_of`
- `related_to`
- `uses_tool`
- `produces_artifact`
- `specializes`
- `demonstrated_by`

### 9.5 PersonSkillState
The subject's current state on a node.

Fields:
- `skill_id`
- `level`
- `xp`
- `confidence`
- `core_self_centrality`
- `recency_score`
- `breadth_score`
- `depth_score`
- `artifact_score`
- `teaching_score`
- `first_seen_at`
- `first_strong_evidence_at`
- `last_evidence_at`
- `last_strong_evidence_at`
- `historical_peak_level`
- `historical_peak_at`
- `status`
- `locked`
- `manual_note`

### 9.6 Claim
Explicit assertions emitted by the extraction pipeline.

Fields:
- `claim_id`
- `claim_type`
- `subject`
- `predicate`
- `object`
- `evidence_ids`
- `confidence`
- `origin` (`observed`, `inferred`, `manual`)

## 10. Skill level model

The UI should look like a game tree, but the stored model should be interpretable.

Recommended levels:
- L0 Unknown / no evidence
- L1 Awareness / exposure
- L2 Assisted practice
- L3 Independent working ability
- L4 Strong builder / owner
- L5 Expert / teacher / recognized authority

Do not infer L4 or L5 from mentions alone.
Consumption-led evidence can support at most L2. L3 and above require stronger action evidence such as implementation, debugging, ownership, teaching, or equivalent artifact-backed signals.

Current mastery and core-self centrality are separate concepts.
- mastery asks "how deep is the demonstrated competence?"
- centrality asks "how foundational or recurrent is this in the person's life and work?"

Each level should be supported by a score vector, not only a single number:
- exposure
- repetition
- recency
- complexity
- artifact ownership
- teaching or mentorship
- cross-context transfer
- external validation

Core-self centrality should be supported by a separate vector, for example:
- time span across years
- recurrence across independent contexts
- number of produced artifacts
- whether adjacent skills depend on it
- whether the person teaches, leads, or self-identifies through it

## 11. Evidence taxonomy

Evidence should be typed because not all signals mean the same thing.

Suggested evidence types:
- `mentioned`
- `studied`
- `implemented`
- `debugged`
- `reviewed`
- `designed`
- `presented`
- `taught`
- `managed`
- `researched`
- `planned`
- `used_tool`
- `produced_artifact`
- `received_feedback`
- `passed_assessment`
- `self_claimed`

Examples:
- a code diff showing a Redis cache implementation -> `implemented`, high reliability
- a note summarizing a paper on Redis -> `studied`, medium reliability
- a chat saying "I should learn Redis someday" -> not enough to claim skill, only interest
- a Twitter/X bio saying "AI engineer" -> self-claim, weak evidence
- a Reddit export with repeated detailed answers about CNC setup -> medium evidence, stronger if corroborated by artifacts
- an AI chat where the person iteratively debugs a real build issue -> medium-to-strong evidence depending on surrounding outputs

### 11.1 Signal taxonomy
The pipeline should preserve lower-weight signal categories rather than pretending they are equivalent to direct proof.

Suggested signal classes:
- `ambient_interest`
- `self_presentation`
- `community_participation`
- `problem_solving_trace`
- `artifact_backed_work`

These classes should affect confidence and interpretation, not only raw level scoring.

## 12. Taxonomy strategy

The system should support three layers of naming:

1. External canonical taxonomies
- ESCO
- O*NET
- optional custom dictionaries

2. Local canonical nodes
- the repo's chosen normalized nodes

3. Surface aliases
- exact phrases found in files
- slang, abbreviations, tool names, internal jargon

Rules:
- in MVP, local canonical nodes are the backbone
- never force every concept into a public taxonomy
- allow freeform local nodes for emerging tech or personal niche topics
- keep links to taxonomy references when available
- store alias mappings separately from node names

## 13. Extraction pipeline

### Stage 0: Discover
- register file
- fingerprint it
- assign parser
- detect whether unchanged

### Stage 1: Parse
- extract text, structure, metadata, and obvious timestamps
- preserve page/line/offset mapping when possible

### Stage 2: Segment
- split into semantically meaningful spans
- preserve headings, code blocks, commit messages, bullet groups

### Stage 3: Classify
- classify source type and likely signal strength
- detect whether the file is authored work, platform-export activity, social trace, AI dialogue, consumption, or ambient metadata

### Stage 4: Extract evidence
- ask extractor model to emit evidence JSON only
- quotes must be copied from the source span
- skill candidates can be raw strings or mapped IDs
- uncertain items go to review instead of silently becoming nodes
- the extractor sees only the current file segment and file-local metadata

### Stage 5: Canonicalize
- deduplicate aliases
- map to existing nodes when confidence is high
- create proposed new nodes when needed

### Stage 6: Update graph
- attach evidence to nodes
- update state vectors
- recompute edges if new evidence supports them

### Stage 7: Recompute person overlay
- update level, xp, recency, confidence, and core-self centrality
- mark low-confidence changes for review
- decay stale skills gently, not aggressively
- preserve historical peak and first-strong-demonstration milestones

### Stage 8: Render artifacts
- update node markdown
- update tree exports
- append to log
- update profile summaries
- update the read-only local viewer bundle

## 14. Prompting / LLM contracts

The system should use multiple narrow prompts instead of one giant omniscient prompt.

### 14.1 Extractor
Input: source segment
Output: strict JSON with evidence records only

Hard rules:
- no summaries unless requested
- no skill levels
- no unsupported prerequisite edges
- quote exact evidence text
- mark uncertainty explicitly

### 14.2 Canonicalizer
Input: evidence records + existing node catalog
Output: mapping decisions

Hard rules:
- prefer existing nodes
- create new nodes only when needed
- preserve alias trail
- never merge two nodes if evidence is ambiguous

### 14.3 Assessor
Input: person evidence history for one node
Output: updated PersonSkillState

Hard rules:
- justify level changes with evidence categories
- treat recency separately from depth
- avoid expertise inflation

### 14.4 Renderer
Input: node state + evidence summaries
Output: markdown pages and tree summaries

Hard rules:
- never hide that something is inferred
- include "Why this exists" and "Level rationale" sections
- link back to evidence IDs and source IDs

## 15. Incremental update rules

1. Never reprocess an unchanged file unless forced.
2. Every derived record remembers its source document hash and pipeline version.
3. When a file changes, only its evidence and impacted nodes are invalidated.
4. Tree layout can be recomputed globally, but node content updates should be local when possible.
5. Manual edits to locked nodes survive automatic runs.
6. Deleting a source removes or soft-retracts the evidence that depended on it.
7. The canonical database stores current state plus append-only run history. Rendered artifacts may be rebuilt from it.

## 16. Confidence model

Store at least three independent confidences:
- extraction confidence
- canonicalization confidence
- assessment confidence

Overall node confidence should be a function of:
- number of evidence items
- source reliability
- evidence diversity
- agreement across sources
- explicit human confirmation

Low-confidence nodes remain visible but flagged.

## 17. Recency and decay

A person may have once known something deeply and now be rusty. The system should capture that.

Store:
- first seen date
- first strong evidence date
- historical peak level
- current active level
- last strong evidence date
- freshness state (`active`, `warming`, `stale`, `historical`)

Do not delete stale skills by default. Mark them as stale.

## 18. Prerequisite modeling

Prerequisites are useful but risky if hallucinated.

Allowed sources for prerequisite edges:
1. imported taxonomy or curated graph
2. human-curated edges

Rules:
- keep `related_to` separate from `prerequisite_of`
- resolve cycles by demoting weak prerequisite claims to `related_to`
- preserve provenance for every non-taxonomy edge
- in MVP, model-suggested prerequisite edges may enter review, but not the canonical graph directly

## 19. Tree rendering model

The underlying graph may not be a pure tree. The UI still needs a tree-like representation.

Recommended render strategy:
- choose major root domains as top branches
- place each skill under one primary parent for rendering
- keep extra relations as side-links
- visualize lock state, current level, and evidence badges
- show first-seen, first-strong, last-strong, and historical-peak markers
- show identity-centrality separately from mastery
- show hidden or low-confidence nodes in a separate review mode

View modes:
- ascii tree in CLI
- mermaid export
- JSON for frontend
- minimal read-only local graph browser
- Obsidian browsing over generated markdown exports

## 20. CLI specification

Working binary name: `traccia`

### 20.1 Repo bootstrap
```bash
traccia init
```

Creates:
- config
- folder layout
- empty database
- default prompts
- default `CLAUDE.md`

### 20.2 Source intake
```bash
traccia add <path>
traccia add-dir <path>
traccia reingest <source-id>
traccia watch <path>
```

### 20.3 Build/update
```bash
traccia ingest <path>
traccia ingest-dir <path>
traccia rebuild
traccia render
```

### 20.4 Query/explain
```bash
traccia tree
traccia tree --format mermaid
traccia node <skill-id>
traccia explain <skill-or-alias>
traccia why <skill-id>
traccia evidence <skill-id>
traccia viewer
```

### 20.5 Review
```bash
traccia review
traccia review --accept <item-id>
traccia review --reject <item-id>
traccia lock <skill-id>
traccia hide <skill-id>
traccia alias add <skill-id> "<alias>"
```

### 20.6 Export
```bash
traccia export graph
traccia export profile
traccia export skill-md
traccia export obsidian
```

### 20.7 Diagnostics
```bash
traccia lint
traccia stats
traccia doctor
```

## 21. Folder layout

```text
traccia/
  config/
    config.yaml
    prompts/
      extract_evidence.md
      canonicalize.md
      assess_skill.md
      render_node.md
  raw/
    inbox/
    imported/
  parsed/
    <source-id>.json
  evidence/
    <source-id>.json
  graph/
    graph.json
    tree.json
    aliases.json
  viewer/
  tree/
    index.md
    log.md
    nodes/
      <skill-id>.md
  profile/
    skill.md
    strengths.md
    gaps.md
  state/
    catalog.sqlite
    manifests/
    review_queue.jsonl
  exports/
```

## 22. Database schema (logical)

Tables:
- `sources`
- `source_spans`
- `evidence_items`
- `skills`
- `skill_aliases`
- `skill_edges`
- `person_skill_states`
- `claims`
- `review_queue`
- `pipeline_runs`
- `manual_overrides`

## 23. Node page format

Example `tree/nodes/python.md`:

```md
---
skill_id: skill.python
kind: skill
name: Python
level: 4
confidence: 0.88
freshness: active
taxonomy_refs:
  - onet:...
aliases:
  - py
last_evidence_at: 2026-03-01
---

# Python

## Summary
Evidence suggests strong independent use across automation, data processing, and tooling.

## Why this exists
- `ev_0012`: implemented CLI utilities in Python
- `ev_0311`: wrote data cleaning scripts
- `ev_0992`: debugged packaging issue

## Level rationale
Current level L4 because the evidence includes repeated authored code, debugging, and multi-context use.

## Related skills
- Packaging
- Data analysis
- Automation

## Gaps / next unlocks
- Async Python
- C extension profiling
```

## 24. Review queue behavior

Items should enter review when:
- a new node is proposed from weak evidence
- two canonical nodes may be duplicates
- a skill level jump is unusually large
- a sensitive source influenced a public-facing profile
- a prerequisite edge was inferred without taxonomy backing

Review item fields:
- `item_id`
- `reason`
- `proposed_change`
- `evidence_ids`
- `risk_level`

## 25. Privacy and security requirements

1. Default to local storage.
2. Allow source path redaction in exports.
3. Support per-source sensitivity labels.
4. Prevent raw secrets from being copied into markdown outputs.
5. Support deletion and full rebuild from remaining sources.
6. Do not export private evidence unless explicitly requested.
7. Keep a clean audit trail of model versions and prompts used.

## 26. Evaluation and success criteria

The system is successful when:
1. A human can inspect any node and understand why it exists.
2. Re-running on unchanged data produces stable results.
3. Adding one new file updates the graph incrementally.
4. The resulting tree feels useful for self-reflection and planning.
5. Precision is high enough that review burden stays manageable.

Key metrics:
- evidence precision
- canonicalization precision
- percentage of nodes with explainable evidence
- graph stability across reruns
- human acceptance rate of proposed nodes
- time to inspect "why do you think I know X?"

## 27. Suggested implementation stack

Recommended default stack:
- Python 3.12
- Typer for CLI
- SQLite for state
- DuckDB optional for analytics
- Pydantic for schemas
- NetworkX for graph operations
- tree-sitter / pygments / git for code evidence
- unstructured / pypdf / python-docx / markdown-it for parsers
- sentence-transformers or API embeddings for alias matching
- optional local model via Ollama
- optional frontend via FastAPI + static JS

Why Python:
- strongest parsing ecosystem
- best graph/data tooling
- simplest path for local AI and document handling

Optional secondary interface:
- TypeScript wrapper or web UI if integrating with an existing Node-based brain CLI
- minimal custom graph browser plus Obsidian-friendly markdown output

## 28. Default decisions for MVP

1. Single-user only.
2. Single-subject graph only.
3. Local files first; connectors later.
4. SQLite is the canonical derived state. Markdown and JSON are projections.
5. Local canonical nodes plus aliases are the backbone. External taxonomy references are optional enrichment.
6. New nodes auto-create only from strong evidence or repeated high-signal mentions. Weak candidates go to review.
7. Consumption-led evidence can reach at most L2.
8. Human review required for any new prerequisite edge not backed by curated import, and model suggestions do not directly enter the canonical graph.
9. MVP ships CLI plus a minimal read-only graph browser and Obsidian-friendly markdown output.
10. Profile outputs are downstream, reflective, and strict-citation-gated.
11. Game-like "XP" exists only as a UI metaphor on top of interpretable signals.
12. Model runtime is pluggable, with local storage and API-default extraction backends.

## 29. Future extensions

- course and resource recommendations tied to missing prerequisites
- quiz-based recalibration
- repository-level skill attribution
- time-based growth timeline
- multi-person team skill maps
- connector support for mail, calendar, issue trackers, and chat
- confidence calibration using human feedback
- public/private export profiles
- broader whole-person archive projections beyond the core skill graph

## 30. Explicit anti-features

Do not ship these in the first version:
- opaque global score with no evidence trail
- auto-publishing private source excerpts
- cross-person comparison by default
- hidden prompt magic that rewrites raw sources
- mandatory cloud backend
- "expert" badges based on weak evidence
- resume-fit scoring or recruiter-oriented ranking
- unified personality or identity graphs mixed into the scored skill model
