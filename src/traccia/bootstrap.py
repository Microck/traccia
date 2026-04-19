from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from traccia.config import default_config, dump_config_text

DEFAULT_PROMPTS = {
    "extract_evidence.md": """# Extract Evidence

You are extracting evidence from one file only.

Return strict JSON matching this shape:
{
  "evidence_items": [
    {
      "evidence_id": "string",
      "source_id": "string",
      "span_start": 0,
      "span_end": 0,
      "quote": "exact quote from the source",
      "evidence_type": "mentioned|studied|implemented|debugged|reviewed|designed|presented|taught|managed|researched|planned|used_tool|produced_artifact|received_feedback|passed_assessment|self_claimed",
      "signal_class": "ambient_interest|self_presentation|community_participation|problem_solving_trace|artifact_backed_work",
      "skill_candidates": ["string"],
      "artifact_candidates": ["string"],
      "time_reference": "YYYY-MM-DD or null",
      "reliability": "tier_a|tier_b|tier_c|tier_d",
      "extractor_version": "string",
      "confidence": 0.0
    }
  ]
}

Rules:
- Use only the current file content.
- Quote exact supporting text.
- Do not assign skill levels.
- Keep weak or ambiguous signals as low-confidence evidence instead of inflating them.
- Distinguish self-presentation, ambient platform activity, and artifact-backed work.
""",
    "canonicalize_skills.md": """# Canonicalize Skills

Map one raw skill candidate onto the local canonical catalog.

Return strict JSON matching:
{
  "candidate_name": "string",
  "action": "create|use_existing|review|ignore",
  "canonical_name": "string or null",
  "skill_id": "string or null",
  "reason": "string",
  "aliases": ["string"],
  "review_risk_level": "low|medium|high"
}

Rules:
- Prefer an existing node when the match is clear.
- Preserve aliases.
- Send ambiguous matches to review.
- Treat weak-signal-only evidence conservatively.
""",
    "score_skill_state.md": """# Score Skill State

Update one person-skill state from grounded evidence history.

Return strict JSON matching:
{
  "level": 0,
  "confidence": 0.0,
  "recency_score": 0.0,
  "breadth_score": 0.0,
  "depth_score": 0.0,
  "artifact_score": 0.0,
  "teaching_score": 0.0,
  "freshness": "active|warming|stale|historical",
  "status": "active|confirmed|disputed|hidden|manual",
  "manual_note": "string or null",
  "rationale": "string"
}

Rules:
- Separate depth from freshness.
- Cap consumption-led evidence at L2.
- Justify every level jump.
- Treat weak signals and self-presentation as materially weaker than artifact-backed work.
""",
    "render_node_page.md": """# Render Node Page

Render one node page from canonical graph state.

Include:
- why this exists
- level rationale
- freshness
- related skills
""",
    "render_tree_index.md": """# Render Tree Index

Render a concise top-level tree index.

Show:
- major branches
- notable strengths
- stale areas
- new unlocks
""",
    "profile_summary.md": """# Profile Summary

Generate a downstream profile summary from accepted graph state only.

Rules:
- exclude uncited claims
- avoid raw excerpts by default
- distinguish current from historical skill
""",
}

DEFAULT_CLAUDE_MD = """# CLAUDE.md

You are the maintainer of a personal skill-tree repository.

Rules:
- Never modify files in `raw/`.
- Evidence comes before inference.
- File-scoped extraction happens before cross-file aggregation.
- The profile is downstream of the graph, not the source of truth.
"""

INITIAL_TREE_INDEX = """# Skill Tree

No skill nodes yet.
"""

INITIAL_TREE_LOG = """# Ingest Log
"""

INITIAL_PROFILE = """# Profile

No exported profile yet.
"""

INITIAL_GRAPH = {
    "nodes": [],
    "edges": [],
    "metadata": {"schema_version": 1, "generated_by": "traccia-phase-0"},
}

INITIAL_TREE_GRAPH = {
    "roots": [],
    "nodes": [],
    "metadata": {"schema_version": 1, "generated_by": "traccia-phase-0"},
}

DATABASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    uri TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_category TEXT NOT NULL DEFAULT 'authored_content',
    parser TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT,
    ingested_at TEXT NOT NULL,
    title TEXT,
    language TEXT,
    sensitivity TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_spans (
    span_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    label TEXT,
    content_hash TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    quote TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    reliability TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    confidence REAL NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_aliases (
    alias_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS skill_edges (
    edge_id TEXT PRIMARY KEY,
    from_skill_id TEXT NOT NULL,
    to_skill_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    weight REAL NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY(from_skill_id) REFERENCES skills(skill_id),
    FOREIGN KEY(to_skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS person_skill_states (
    skill_id TEXT PRIMARY KEY,
    level INTEGER NOT NULL,
    xp REAL NOT NULL,
    confidence REAL NOT NULL,
    core_self_centrality REAL NOT NULL DEFAULT 0,
    recency_score REAL NOT NULL,
    breadth_score REAL NOT NULL,
    depth_score REAL NOT NULL,
    artifact_score REAL NOT NULL,
    teaching_score REAL NOT NULL,
    first_seen_at TEXT,
    first_learned_at TEXT,
    first_strong_evidence_at TEXT,
    last_evidence_at TEXT,
    last_strong_evidence_at TEXT,
    historical_peak_level INTEGER,
    historical_peak_at TEXT,
    acquired_at TEXT,
    acquisition_basis TEXT,
    freshness TEXT NOT NULL,
    status TEXT NOT NULL,
    locked INTEGER NOT NULL DEFAULT 0,
    manual_note TEXT,
    FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    claim_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL,
    origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_queue (
    item_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    proposed_change_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    step_name TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS manual_overrides (
    override_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DIRECTORIES = (
    "config",
    "config/prompts",
    "raw/inbox",
    "raw/imported",
    "parsed",
    "evidence",
    "graph",
    "viewer",
    "tree",
    "tree/nodes",
    "profile",
    "state",
    "state/manifests",
    "exports",
)

FILES = {
    "tree/index.md": INITIAL_TREE_INDEX,
    "tree/log.md": INITIAL_TREE_LOG,
    "profile/skill.md": INITIAL_PROFILE,
    "profile/strengths.md": INITIAL_PROFILE.replace("Profile", "Strengths"),
    "profile/gaps.md": INITIAL_PROFILE.replace("Profile", "Gaps"),
    "profile/artifacts.md": INITIAL_PROFILE.replace("Profile", "Artifacts"),
    "state/review_queue.jsonl": "",
    "CLAUDE.md": DEFAULT_CLAUDE_MD,
}

JSON_FILES = {
    "graph/graph.json": INITIAL_GRAPH,
    "graph/tree.json": INITIAL_TREE_GRAPH,
}


@dataclass(slots=True)
class RepoInitializer:
    project_root: Path
    force: bool = False

    def initialize(self) -> None:
        self.project_root.mkdir(parents=True, exist_ok=True)

        for directory in DIRECTORIES:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)

        self._write_text(
            self.project_root / "config" / "config.yaml",
            dump_config_text(default_config()),
        )

        for prompt_name, prompt_text in DEFAULT_PROMPTS.items():
            self._write_text(self.project_root / "config" / "prompts" / prompt_name, prompt_text)

        for relative_path, text in FILES.items():
            self._write_text(self.project_root / relative_path, text)

        for relative_path, payload in JSON_FILES.items():
            self._write_json(self.project_root / relative_path, payload)

        self._initialize_database(self.project_root / "state" / "catalog.sqlite")

    def _write_text(self, path: Path, content: str) -> None:
        if path.exists() and not self.force:
            return
        path.write_text(content)

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        if path.exists() and not self.force:
            return
        path.write_text(json.dumps(payload, indent=2) + "\n")

    def _initialize_database(self, path: Path) -> None:
        if path.exists() and not self.force:
            return

        connection = sqlite3.connect(path)
        try:
            connection.executescript(DATABASE_SCHEMA)
            connection.commit()
        finally:
            connection.close()
