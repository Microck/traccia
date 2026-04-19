# plan

## 1. Build strategy

Build the system in narrow, reviewable layers. Do not start with a big autonomous agent that tries to do everything at once. The order should be:

1. immutable source intake
2. deterministic parsing and span tracking
3. evidence extraction
4. canonical skill graph
5. person-state scoring
6. tree rendering and explainability
7. optional profile/wiki generation

This keeps the hardest part, skill inference, grounded in evidence from day one.
The file-by-file synthesis contract is mandatory. Cross-file aggregation happens only after a file has yielded its own evidence.

## 2. Default implementation choice

Use Python for the first implementation.
Reason:
- easier file parsing
- better graph and NLP libraries
- easier local model integration
- simpler JSON schema enforcement

If you later want parity with an existing Node CLI, wrap the Python core instead of reversing this decision early.

## 3. Milestone sequence

### Phase 0: Repository skeleton and contracts
Deliverables:
- repo scaffold
- folder layout
- Pydantic models
- config file
- prompt files
- test fixtures
- empty CLI commands

Done when:
- `traccia init` works
- schema validation works
- golden test fixtures load

### Phase 1: Source intake and parsing
Build:
- source catalog
- file fingerprinting
- parser registry
- parse-to-JSON normalized format
- span/offset preservation
- source-category classification for stronger vs weaker signal types
- ignore unchanged files

Done when:
- supported test files parse into a stable normalized document schema
- rerunning on unchanged inputs is a no-op
- source deletion and reingest logic works

### Phase 2: Evidence extraction
Build:
- segmenter
- extractor prompt
- strict JSON output validation
- evidence typing
- weak-signal classification
- file-scoped extraction contract
- review queue for uncertain extractions

Done when:
- each parsed file can produce evidence JSON
- evidence items keep exact source spans
- invalid model output is rejected and retried safely
- extraction for one file does not depend on wider corpus context

### Phase 3: Canonicalization and node registry
Build:
- alias resolver
- node creation rules
- local-first canonical node registry
- optional taxonomy reference adapters
- skill registry
- merge / split review flow

Done when:
- repeated aliases map to the same node when appropriate
- ambiguous mappings go to review instead of silently merging
- new nodes get stable IDs
- external taxonomy references remain optional enrichment, not the backbone

### Phase 4: Person-state scoring
Build:
- level model
- confidence model
- recency model
- skill decay rules
- historical peak state tracking
- first-seen / first-strong timeline tracking
- core-self centrality model
- consumption-evidence cap rules

Done when:
- every node can show current level, confidence, and freshness
- every node can show first seen, first strong evidence, and historical peak timing
- current mastery and identity-centrality remain separate signals
- adding new evidence updates only impacted states
- stale skills remain visible but flagged
- consumption-led evidence cannot push a node beyond L2

### Phase 5: Graph and prerequisite layer
Build:
- edge registry
- parent/part/prerequisite/related rules
- cycle handling
- curated prerequisite imports
- manual edge curation

Done when:
- graph export is stable
- prerequisite edges come only from curated imports or explicit human curation
- cycles are either resolved or downgraded to `related_to`

### Phase 6: Rendered artifacts
Build:
- node markdown renderer
- tree index renderer
- append-only log
- graph JSON export
- ASCII / Mermaid CLI output
- minimal custom graph browser
- Obsidian-friendly markdown export

Done when:
- `traccia tree` is useful in the terminal
- `traccia explain <skill>` shows clear evidence and rationale
- the markdown artifact folder is readable without the database
- the graph browser is useful for read-only traversal
- generated markdown remains pleasant to browse in Obsidian

### Phase 7: Review UX
Build:
- review queue browser in CLI
- accept/reject/lock commands
- manual alias additions
- hidden/private node flags

Done when:
- a user can safely curate the graph without editing the database directly
- locked nodes survive rebuilds
- review burden is low enough to be practical

### Phase 8: Optional profile generation
Build:
- `profile/skill.md`
- strengths, gaps, and timeline summaries
- artifacts summary
- identity-centrality summaries
- strict cited export rules

Done when:
- the profile is generated from the graph, not directly from raw files
- all claims in the profile can be traced back to graph nodes and evidence
- uncited or sensitive claims are excluded by default

## 4. MVP scope

Include:
- local CLI
- minimal custom graph browser
- Obsidian-friendly markdown export
- markdown/text/pdf/docx/code ingestion
- evidence extraction
- canonical nodes + aliases
- skill state scoring
- explainability
- markdown + JSON exports
- full reflective profile set with strict cited export gates

Exclude:
- connectors
- multi-user auth
- cloud sync
- automatic course recommendation
- browser extension
- full personality graph / identity modeling
- recruiter or job-fit workflows
- fancy web app

## 5. Critical implementation rules

1. The LLM never writes into `raw/`.
2. Every automatic change must be attributable to a pipeline step and version.
3. Evidence extraction and scoring are separate steps.
4. Manual locks override automation.
5. New nodes from weak evidence must go to review.
6. Tree rendering is a projection of the graph, not the source of truth.
7. The profile view must depend on the graph, not bypass it.
8. SQLite is the canonical derived state. Markdown and JSON are projections.
9. Extraction is file-scoped first. Cross-file reasoning starts after evidence extraction.
10. Local canonical nodes are the backbone. External taxonomies are optional references.
11. Consumption-led evidence can reach at most L2.
12. In MVP, `prerequisite_of` edges are curated-only.
13. Ambient platform signals must never be treated as equivalent to artifact-backed work.
14. Current mastery and core-self centrality are separate output dimensions.

## 6. Recommended repository layout

```text
repo/
  src/
    traccia/
      cli/
      config/
      parsers/
      segmentation/
      extraction/
      canonicalization/
      scoring/
      graph/
      rendering/
      review/
      storage/
  prompts/
  tests/
    fixtures/
    golden/
  docs/
```

## 7. Test strategy

### 7.1 Golden fixtures
Create a small corpus with:
- a project README
- code files
- notes
- a PDF
- a calendar export
- a chat export

Expected outputs:
- parsed documents
- extracted evidence
- graph JSON
- rendered node pages

### 7.2 Stability tests
- rerun on unchanged corpus
- expect identical outputs except timestamps where intentionally excluded

### 7.3 Mutation tests
- modify one file
- confirm only impacted nodes change

### 7.4 Safety tests
- files containing API keys or secrets should not leak into public profile output

### 7.5 Review tests
- ambiguous aliases should land in review queue

## 8. Open questions to settle early

1. Should `topic` and `skill` remain distinct in the UI, or only in storage?
2. What exact confidence threshold should trigger strong-evidence auto-creation of a new node?
3. How aggressive should recency decay be?
4. Which source types deserve the strongest reliability weights?
5. Which auxiliary facet vocabulary should be supported for lightly modeled non-skill context?

Make these configurable, but choose defaults early so the system behaves consistently.

## 9. Recommended prompt inventory

- `extract_evidence.md`
- `canonicalize_skills.md`
- `score_skill_state.md`
- `render_node_page.md`
- `render_tree_index.md`
- `profile_summary.md`

Keep them small and role-specific.

## 10. Suggested first demo corpus

Use a single person's data bundle with:
- one repo
- one project design doc
- one talk or presentation
- a month of notes
- selected calendar entries
- a few bookmarks or article summaries

This mix is enough to demonstrate:
- studied vs built distinction
- recency
- artifact-based leveling
- curated prerequisite suggestions
- explainability

## 11. What to build before LLM tuning

Implement these before spending time on prompt polish:
- parser registry
- normalized document schema
- evidence JSON schema
- alias store
- stable IDs
- review queue
- graph projection rules

Without these, prompt tuning will not save the system.

## 12. What to harden after the first working build

After the first build works end-to-end, harden:
- caching
- retry logic
- structured logging
- prompt versioning
- migration scripts
- secret redaction
- export privacy controls
- graph diff tooling

## 13. Minimum acceptance checklist

The project is ready for real-world use when all of the following are true:
- one command can ingest a directory
- unchanged files are skipped
- at least 80 percent of displayed skill nodes have direct evidence links
- every node page explains why the node exists
- manual locks and review decisions persist
- graph export and markdown export remain consistent
- profile exports never contain uncited private claims
- the read-only graph browser and Obsidian export stay consistent with the canonical graph

## 14. Later extension path

After the CLI is stable:
1. timeline / history mode
2. connector adapters
3. recommended next skills
4. team-level aggregate maps
5. import/export packs for portability
6. broader whole-person archive projections beyond the skill graph

Do not start here. Start with correctness and provenance.
