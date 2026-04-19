# decisions

This document records the planning conversation so far from start to finish, including the product clarifications, locked implementation decisions, and the GitHub reference research that followed.

## 1. Starting point

The initial spec established `traccia` as:
- a local-first CLI
- an evidence-backed skill tree
- incremental, file-by-file ingestion
- immutable raw sources
- explainable skill claims
- optional profile/wiki output downstream of the graph

The early build plan already favored:
- Python first
- narrow, reviewable phases
- evidence extraction before graph or scoring sophistication
- correctness and provenance before UI polish

## 2. Clarifications locked during the planning conversation

### 2.1 Product framing

The project is **not job-searching oriented**.

The correct framing is:
- reflective self-profile archiving
- skill-graph-first
- evidence-backed self-understanding

This means:
- the main artifact is the skill graph
- profile outputs are downstream reflections of the graph
- recruiter or resume-style ranking logic is not a core product goal

### 2.2 File-by-file synthesis

This became a hard architectural rule:
- each file is parsed, segmented, and synthesized independently first
- first-pass extraction uses only the current file and file-local metadata
- cross-file aggregation happens later in canonicalization, scoring, and rendering

This was locked specifically to avoid a corpus-level omniscient summarizer in the critical path.

### 2.3 Skill graph first, archive later

A broader whole-person archive vision was acknowledged, but MVP and v1 remain skill-graph-first.

Current decision:
- broader non-skill material may be ingested
- in MVP it is only modeled lightly as auxiliary metadata or facets
- it does not become first-class scored graph nodes

This preserves the long-term archive direction without collapsing the product into a vague identity graph.

## 3. Locked design decisions

### 3.1 Canonical state

- SQLite is the canonical derived state.
- Markdown and JSON are projections.
- The system keeps current state plus append-only run history and provenance.

### 3.2 Canonical node strategy

- local canonical nodes plus aliases are the backbone
- external taxonomies such as ESCO or O*NET are optional references
- taxonomy should enrich, not dominate, the graph

### 3.3 New node creation

- auto-create only from strong evidence or repeated high-signal mentions
- weak candidates go to review

### 3.4 Scoring boundaries

- consumption-led evidence may contribute to awareness and learning
- consumption-led evidence is capped at `L2`
- `L3+` requires stronger action evidence such as implementation, debugging, ownership, teaching, or equivalent artifact-backed proof

### 3.5 Prerequisite edges

For MVP:
- `prerequisite_of` is curated-only
- allowed sources are imported curated taxonomy or explicit human curation
- model suggestions may enter review, but not the canonical graph directly

### 3.6 Interface scope

MVP now includes:
- CLI
- minimal read-only custom graph browser
- Obsidian-friendly markdown export

Obsidian is an export and browsing target, not the primary interactive graph product.

### 3.7 Profile generation

The planning conversation kept full profile outputs in MVP, but under strict gates:
- downstream from the graph only
- accepted or high-confidence non-sensitive claims only
- no raw excerpts by default
- every claim traceable to graph nodes and evidence

### 3.8 Model runtime

- pluggable model runtime
- local storage always
- API-default extraction backend for MVP
- local models remain a supported path, not a blocker

## 4. Consequences for implementation

The current intended flow is:

1. ingest one file
2. parse and preserve spans
3. extract evidence from only that file
4. validate strict JSON
5. canonicalize against existing node catalog
6. update person-state scoring
7. update graph projections
8. update markdown, JSON, viewer, and append-only log

Important implication:
- no cross-file context at extraction time
- no direct profile writing from raw files
- no prerequisite hallucination path in MVP

## 5. GitHub research summary

The GitHub research confirmed that there is no strong open-source exact match for `traccia`.

What exists today is stronger in two adjacent categories:
- LLM wiki / knowledge-compilation systems
- graph viewers and graph-report tools

The obvious "skill graph" repos are mostly the wrong domain because they are:
- resume-driven
- job-fit-oriented
- onboarding or learning-path systems

## 6. Borrow / avoid matrix

| Repo | Role | Decision |
|---|---|---|
| `atomicmemory/llm-wiki-compiler` | closest conceptual seed | borrow architecture heavily |
| `swarmclawai/swarmvault` | provenance and review donor | borrow selected subsystems only |
| `SamurAIGPT/llm-wiki-agent` | repo and export convention donor | borrow conventions, not engine |
| `nashsu/llm_wiki` | polished product and queue UX donor | borrow UI ideas only |
| `safishamsi/graphify` | graph packaging and certainty-label donor | borrow graph semantics and reporting |
| `Lum1104/Understand-Anything` | graph viewer donor | borrow viewer patterns only |
| `RoninATX/Human-Skill-Tree` | visual motif | UI reference only |
| `nshadov/personal-skill-tree` | visual motif | UI reference only |
| `NickSaulnier/SkillGraph` and similar repos | hiring / job-fit anti-reference | do not build from |
| `saxenauts/persona` / `hanig/engram` | whole-person archive caution references | read for warnings, not as a base |

## 7. Current build stance

The strongest current recommendation is:

- build `traccia` from scratch
- borrow patterns rather than forking a repo
- treat `atomicmemory/llm-wiki-compiler` as the closest conceptual parent
- treat `swarmvault` as the richest donor for provenance, approvals, and graph/report patterns
- treat graph viewers as separate reference material, not as a product foundation

## 8. Unresolved calibration questions

These were intentionally left open for later calibration against a golden corpus rather than guessed in prose:

- exact confidence threshold for strong-evidence auto-creation
- recency decay curve
- source reliability weights
- exact auxiliary facet vocabulary for lightly modeled non-skill context
- whether `topic` and `skill` remain distinct in the UI or only in storage

## 9. Summary

The conversation narrowed the project substantially.

What `traccia` is now:
- a local-first reflective self-profile archive
- centered on a skill graph
- driven by file-by-file evidence extraction
- backed by SQLite as canonical state
- explainable, reviewable, and provenance-heavy
- exportable to markdown, JSON, a minimal graph browser, and a cited reflective profile set

What it is not:
- a resume scorer
- a recruiter tool
- a generic whole-person identity graph
- a corpus-level summarizer that jumps straight to conclusions

## 10. Archive-breadth update

The archive boundary widened again after the initial build:
- Reddit exports
- Google exports
- Twitter/X exports
- AI conversation exports
- social media profiles
- and other personal data exports are now in scope as inputs

This does **not** change the core product into an undifferentiated identity graph.
The updated stance is:

### 10.1 Everything may be ingested, but not everything is proof

The system should preserve broad digital traces without allowing them to inflate competence claims.

Therefore the model is now conceptually split into four layers:
1. canonical skill graph
2. evidence layer
3. person skill overlay
4. identity overlay

### 10.2 Mastery and identity are separate

Two distinct questions must be represented:
- "How deep is the demonstrated competence?"
- "How central is this to the person's recurring self and long-term practice?"

This means current mastery and core-self centrality must not collapse into one score.

### 10.3 Weak-signal discipline is locked

The following are useful but weak by default:
- search history
- bookmarks
- follows / likes / reposts
- short social posts
- profile bios
- AI chats without surrounding artifact evidence

These may support:
- awareness
- interest
- identity context
- review hints

They must not independently drive high skill levels.

### 10.4 Node outputs must answer timeline and placement questions

Node pages should eventually answer:
- where this skill fits
- when it first appeared
- when it was first strongly demonstrated
- when it peaked
- how current it is
- what it connects to
- how deep the competence is
- how central it is to the person's overall self-model
