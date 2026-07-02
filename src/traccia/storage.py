from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from traccia.models import (
    EvidenceItem,
    ParsedSpan,
    PersonSkillState,
    ReviewItem,
    SkillEdge,
    SkillNode,
    SourceDocument,
)

SQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SQLITE_BUSY_TIMEOUT_MS = 300_000
SQLITE_CONNECT_TIMEOUT_SECONDS = SQLITE_BUSY_TIMEOUT_MS / 1000
SQLITE_LOCK_RETRY_ATTEMPTS = 5


def _is_sqlite_lock_error(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message


class Storage:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.db_path = project_root / "state" / "catalog.sqlite"

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.db_path,
            timeout=SQLITE_CONNECT_TIMEOUT_SECONDS,
        )
        connection.row_factory = sqlite3.Row
        try:
            self._configure_connection_with_retries(connection)
            self._ensure_schema_with_retries(connection)
            yield connection
            self._commit_with_retries(connection)
        finally:
            connection.close()

    def _configure_connection(self, connection: sqlite3.Connection) -> None:
        connection.execute(f"pragma busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        connection.execute("pragma journal_mode = WAL")
        connection.execute("pragma synchronous = NORMAL")

    def _configure_connection_with_retries(self, connection: sqlite3.Connection) -> None:
        for attempt_index in range(SQLITE_LOCK_RETRY_ATTEMPTS):
            try:
                self._configure_connection(connection)
                return
            except sqlite3.OperationalError as exc:
                if not _is_sqlite_lock_error(exc) or attempt_index == SQLITE_LOCK_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(1.0 + attempt_index)

    def _ensure_schema_with_retries(self, connection: sqlite3.Connection) -> None:
        for attempt_index in range(SQLITE_LOCK_RETRY_ATTEMPTS):
            try:
                self._ensure_schema(connection)
                return
            except sqlite3.OperationalError as exc:
                if not _is_sqlite_lock_error(exc) or attempt_index == SQLITE_LOCK_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(1.0 + attempt_index)

    def _commit_with_retries(self, connection: sqlite3.Connection) -> None:
        for attempt_index in range(SQLITE_LOCK_RETRY_ATTEMPTS):
            try:
                connection.commit()
                return
            except sqlite3.OperationalError as exc:
                if not _is_sqlite_lock_error(exc) or attempt_index == SQLITE_LOCK_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(1.0 + attempt_index)

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        # Static bootstrap SQL is safe to run as a script. SQLite does not support binding table
        # or column identifiers, so additive schema updates validate identifiers before formatting.
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS extraction_checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                extractor_version TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_fingerprint TEXT NOT NULL,
                evidence_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_id, chunk_index)
            );

            CREATE TABLE IF NOT EXISTS graph_candidate_cache (
                candidate_name TEXT NOT NULL,
                support_fingerprint TEXT NOT NULL,
                canonical_decision_json TEXT NOT NULL,
                score_payload_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(candidate_name, support_fingerprint)
            );

            CREATE TABLE IF NOT EXISTS graph_skill_score_cache (
                skill_id TEXT NOT NULL,
                evidence_fingerprint TEXT NOT NULL,
                score_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(skill_id, evidence_fingerprint)
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
            """
        )
        self._ensure_columns(
            connection,
            table="person_skill_states",
            columns={
                "core_self_centrality": "REAL NOT NULL DEFAULT 0",
                "first_seen_at": "TEXT",
                "first_learned_at": "TEXT",
                "first_strong_evidence_at": "TEXT",
                "last_strong_evidence_at": "TEXT",
                "historical_peak_level": "INTEGER",
                "historical_peak_at": "TEXT",
                "acquired_at": "TEXT",
                "acquisition_basis": "TEXT",
            },
        )
        self._ensure_columns(
            connection,
            table="sources",
            columns={
                "source_category": "TEXT NOT NULL DEFAULT 'authored_content'",
            },
        )

    def _ensure_columns(
        self,
        connection: sqlite3.Connection,
        *,
        table: str,
        columns: dict[str, str],
    ) -> None:
        _validate_sql_identifier(table)
        for column_name in columns:
            _validate_sql_identifier(column_name)
        existing = {
            row["name"]
            for row in connection.execute(f"pragma table_info({table})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name in existing:
                continue
            connection.execute(
                f"alter table {table} add column {column_name} {column_type}"
            )

    def fetch_source(self, source_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("select * from sources where source_id = ?", (source_id,)).fetchone()
            return dict(row) if row else None

    def list_sources(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("select * from sources order by source_id").fetchall()
            return [dict(row) for row in rows]

    def mark_source_deleted(self, source_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "update sources set status = 'deleted' where source_id = ?",
                (source_id,),
            )

    def delete_source_derived_records(self, source_id: str) -> None:
        with self.connect() as connection:
            connection.execute("delete from evidence_items where source_id = ?", (source_id,))
            connection.execute("delete from source_spans where source_id = ?", (source_id,))
            connection.execute("delete from extraction_checkpoints where source_id = ?", (source_id,))

    def clear_pending_review_items(self) -> None:
        with self.connect() as connection:
            connection.execute("delete from review_queue where status = 'pending'")

    def upsert_source(self, source: SourceDocument) -> None:
        payload = source.model_dump(mode="json")
        with self.connect() as connection:
            connection.execute(
                """
                insert into sources (
                    source_id, uri, source_type, source_category, parser, sha256, created_at, ingested_at,
                    title, language, sensitivity, metadata_json, status
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(source_id) do update set
                    uri = excluded.uri,
                    source_type = excluded.source_type,
                    source_category = excluded.source_category,
                    parser = excluded.parser,
                    sha256 = excluded.sha256,
                    created_at = excluded.created_at,
                    ingested_at = excluded.ingested_at,
                    title = excluded.title,
                    language = excluded.language,
                    sensitivity = excluded.sensitivity,
                    metadata_json = excluded.metadata_json,
                    status = excluded.status
                """,
                (
                    payload["source_id"],
                    payload["uri"],
                    payload["source_type"],
                    payload["source_category"],
                    payload["parser"],
                    payload["sha256"],
                    payload["created_at"],
                    payload["ingested_at"],
                    payload["title"],
                    payload["language"],
                    payload["sensitivity"],
                    json.dumps(payload["metadata"], sort_keys=True),
                    payload["status"],
                ),
            )

    def replace_source_spans(self, source_id: str, spans: list[ParsedSpan]) -> None:
        with self.connect() as connection:
            connection.execute("delete from source_spans where source_id = ?", (source_id,))
            seen_span_ids: set[str] = set()
            for index, span in enumerate(spans):
                span_id = span.span_id
                if span_id in seen_span_ids:
                    span_id = f"{span.span_id}::{index}"
                    while span_id in seen_span_ids:
                        span_id = f"{span.span_id}::{index}:{len(seen_span_ids)}"
                suffix = 0
                while True:
                    try:
                        connection.execute(
                            """
                            insert into source_spans (
                                span_id, source_id, span_start, span_end, label, content_hash
                            ) values (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                span_id,
                                source_id,
                                span.span_start,
                                span.span_end,
                                span.segment_kind,
                                span_id,
                            ),
                        )
                        seen_span_ids.add(span_id)
                        break
                    except sqlite3.IntegrityError as exc:
                        if "source_spans.span_id" not in str(exc):
                            raise
                        # span_id is the table primary key. Older parsers and some structured
                        # exports can collide across sources, so keep the parser's preferred ID
                        # when possible and add a stable source-scoped suffix only on collision.
                        suffix += 1
                        span_id = f"{span.span_id}::{source_id}:{index}:{suffix}"

    def replace_source_evidence(self, source_id: str, evidence_items: list[EvidenceItem]) -> None:
        with self.connect() as connection:
            connection.execute("delete from evidence_items where source_id = ?", (source_id,))
            for evidence_item in evidence_items:
                payload = evidence_item.model_dump(mode="json")
                connection.execute(
                    """
                    insert into evidence_items (
                        evidence_id, source_id, span_start, span_end, quote, evidence_type,
                        reliability, extractor_version, confidence, payload_json
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["evidence_id"],
                        payload["source_id"],
                        payload["span_start"],
                        payload["span_end"],
                        payload["quote"],
                        payload["evidence_type"],
                        payload["reliability"],
                        payload["extractor_version"],
                        payload["confidence"],
                        json.dumps(payload, sort_keys=True),
                    ),
                )

    def upsert_extraction_checkpoint(
        self,
        *,
        source_id: str,
        source_sha256: str,
        extractor_version: str,
        chunk_index: int,
        chunk_fingerprint: str,
        evidence_items: list[EvidenceItem],
    ) -> None:
        checkpoint_id = f"{source_id}::{chunk_index}"
        payload = json.dumps(
            [item.model_dump(mode="json") for item in evidence_items],
            sort_keys=True,
        )
        with self.connect() as connection:
            connection.execute(
                """
                insert into extraction_checkpoints (
                    checkpoint_id, source_id, source_sha256, extractor_version,
                    chunk_index, chunk_fingerprint, evidence_json, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                on conflict(source_id, chunk_index) do update set
                    checkpoint_id = excluded.checkpoint_id,
                    source_sha256 = excluded.source_sha256,
                    extractor_version = excluded.extractor_version,
                    chunk_fingerprint = excluded.chunk_fingerprint,
                    evidence_json = excluded.evidence_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    checkpoint_id,
                    source_id,
                    source_sha256,
                    extractor_version,
                    chunk_index,
                    chunk_fingerprint,
                    payload,
                ),
            )

    def list_extraction_checkpoints(self, source_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                select *
                from extraction_checkpoints
                where source_id = ?
                order by chunk_index
                """,
                (source_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def clear_extraction_checkpoints(self, source_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "delete from extraction_checkpoints where source_id = ?",
                (source_id,),
            )

    def fetch_graph_candidate_cache(
        self,
        *,
        candidate_name: str,
        support_fingerprint: str,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                select *
                from graph_candidate_cache
                where candidate_name = ? and support_fingerprint = ?
                """,
                (candidate_name, support_fingerprint),
            ).fetchone()
            return dict(row) if row else None

    def list_graph_candidate_cache_rows(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                select candidate_name, support_fingerprint, canonical_decision_json, score_payload_json
                from graph_candidate_cache
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def upsert_graph_candidate_cache(
        self,
        *,
        candidate_name: str,
        support_fingerprint: str,
        canonical_decision_json: str,
        score_payload_json: str | None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into graph_candidate_cache (
                    candidate_name,
                    support_fingerprint,
                    canonical_decision_json,
                    score_payload_json,
                    updated_at
                ) values (?, ?, ?, ?, CURRENT_TIMESTAMP)
                on conflict(candidate_name, support_fingerprint) do update set
                    canonical_decision_json = excluded.canonical_decision_json,
                    score_payload_json = excluded.score_payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    candidate_name,
                    support_fingerprint,
                    canonical_decision_json,
                    score_payload_json,
                ),
            )

    def fetch_graph_skill_score_cache(
        self,
        *,
        skill_id: str,
        evidence_fingerprint: str,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                select *
                from graph_skill_score_cache
                where skill_id = ? and evidence_fingerprint = ?
                """,
                (skill_id, evidence_fingerprint),
            ).fetchone()
            return dict(row) if row else None

    def list_graph_skill_score_cache_rows(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                select skill_id, evidence_fingerprint, score_payload_json
                from graph_skill_score_cache
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def upsert_graph_skill_score_cache(
        self,
        *,
        skill_id: str,
        evidence_fingerprint: str,
        score_payload_json: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into graph_skill_score_cache (
                    skill_id,
                    evidence_fingerprint,
                    score_payload_json,
                    updated_at
                ) values (?, ?, ?, CURRENT_TIMESTAMP)
                on conflict(skill_id, evidence_fingerprint) do update set
                    score_payload_json = excluded.score_payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (skill_id, evidence_fingerprint, score_payload_json),
            )

    def count_graph_skill_score_cache_rows(self) -> int:
        with self.connect() as connection:
            row = connection.execute("select count(*) as count from graph_skill_score_cache").fetchone()
            return int(row["count"])

    def upsert_pipeline_run(
        self,
        *,
        run_id: str,
        step_name: str,
        pipeline_version: str,
        status: str,
        started_at: str,
        completed_at: str | None,
        details: dict[str, Any],
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into pipeline_runs (
                    run_id, step_name, pipeline_version, status, started_at,
                    completed_at, details_json
                ) values (?, ?, ?, ?, ?, ?, ?)
                on conflict(run_id) do update set
                    status = excluded.status,
                    completed_at = excluded.completed_at,
                    details_json = excluded.details_json
                """,
                (
                    run_id,
                    step_name,
                    pipeline_version,
                    status,
                    started_at,
                    completed_at,
                    json.dumps(details, sort_keys=True),
                ),
            )

    def fetch_pipeline_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "select * from pipeline_runs where run_id = ?",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_evidence(self) -> list[EvidenceItem]:
        with self.connect() as connection:
            rows = connection.execute("select payload_json from evidence_items order by evidence_id").fetchall()
            return [EvidenceItem.model_validate_json(row["payload_json"]) for row in rows]

    def list_source_evidence(self, source_id: str) -> list[EvidenceItem]:
        with self.connect() as connection:
            rows = connection.execute(
                "select payload_json from evidence_items where source_id = ? order by evidence_id",
                (source_id,),
            ).fetchall()
            return [EvidenceItem.model_validate_json(row["payload_json"]) for row in rows]

    def replace_graph(
        self,
        *,
        skills: list[SkillNode],
        states: list[PersonSkillState],
        edges: list[SkillEdge],
    ) -> None:
        with self.connect() as connection:
            connection.execute("delete from skill_aliases")
            connection.execute("delete from skill_edges")
            connection.execute("delete from person_skill_states")
            connection.execute("delete from skills")

            for skill in skills:
                payload = skill.model_dump(mode="json")
                connection.execute(
                    """
                    insert into skills (skill_id, kind, name, slug, description, status, created_by, last_updated)
                    values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["skill_id"],
                        payload["kind"],
                        payload["name"],
                        payload["slug"],
                        payload["description"],
                        payload["status"],
                        payload["created_by"],
                        payload["last_updated"],
                    ),
                )
                for alias in sorted(set(payload["aliases"])):
                    alias_id = f"{payload['skill_id']}::{alias.lower()}"
                    connection.execute(
                        """
                        insert into skill_aliases (alias_id, skill_id, alias, source, confidence)
                        values (?, ?, ?, ?, ?)
                        """,
                        (alias_id, payload["skill_id"], alias, "graph-build", 1.0),
                    )

            for state in states:
                payload = state.model_dump(mode="json")
                connection.execute(
                    """
                    insert into person_skill_states (
                        skill_id, level, xp, confidence, core_self_centrality, recency_score, breadth_score,
                        depth_score, artifact_score, teaching_score, first_seen_at, first_learned_at,
                        first_strong_evidence_at, last_evidence_at, last_strong_evidence_at,
                        historical_peak_level, historical_peak_at, acquired_at, acquisition_basis,
                        freshness, status, locked, manual_note
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["skill_id"],
                        payload["level"],
                        payload["xp"],
                        payload["confidence"],
                        payload["core_self_centrality"],
                        payload["recency_score"],
                        payload["breadth_score"],
                        payload["depth_score"],
                        payload["artifact_score"],
                        payload["teaching_score"],
                        payload["first_seen_at"],
                        payload["first_learned_at"],
                        payload["first_strong_evidence_at"],
                        payload["last_evidence_at"],
                        payload["last_strong_evidence_at"],
                        payload["historical_peak_level"],
                        payload["historical_peak_at"],
                        payload["acquired_at"],
                        payload["acquisition_basis"],
                        payload["freshness"],
                        payload["status"],
                        int(payload["locked"]),
                        payload["manual_note"],
                    ),
                )

            for edge in edges:
                payload = edge.model_dump(mode="json")
                connection.execute(
                    """
                    insert into skill_edges (
                        edge_id, from_skill_id, to_skill_id, edge_type, weight, source, confidence
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["edge_id"],
                        payload["from_skill_id"],
                        payload["to_skill_id"],
                        payload["edge_type"],
                        payload["weight"],
                        payload["source"],
                        payload["confidence"],
                    ),
                )

    def list_skill_rows(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                select s.*, p.level, p.xp, p.confidence as state_confidence, p.recency_score,
                       p.core_self_centrality, p.breadth_score, p.depth_score, p.artifact_score,
                       p.teaching_score, p.first_seen_at, p.first_learned_at, p.first_strong_evidence_at,
                       p.last_evidence_at, p.last_strong_evidence_at, p.historical_peak_level,
                       p.historical_peak_at, p.acquired_at, p.acquisition_basis, p.freshness,
                       p.status as state_status, p.locked, p.manual_note
                from skills s
                left join person_skill_states p on p.skill_id = s.skill_id
                order by s.kind, s.name
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def list_edges(self) -> list[SkillEdge]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                select edge_id, from_skill_id, to_skill_id, edge_type, weight, source, confidence
                from skill_edges
                order by edge_id
                """
            ).fetchall()
            return [SkillEdge.model_validate(dict(row)) for row in rows]

    def find_skill_by_lookup(self, lookup: str) -> dict[str, Any] | None:
        normalized = lookup.lower()
        with self.connect() as connection:
            row = connection.execute(
                """
                select s.*, p.level, p.xp, p.confidence as state_confidence, p.recency_score,
                       p.core_self_centrality, p.breadth_score, p.depth_score, p.artifact_score,
                       p.teaching_score, p.first_seen_at, p.first_learned_at, p.first_strong_evidence_at,
                       p.last_evidence_at, p.last_strong_evidence_at, p.historical_peak_level,
                       p.historical_peak_at, p.acquired_at, p.acquisition_basis, p.freshness,
                       p.status as state_status, p.locked, p.manual_note
                from skills s
                left join person_skill_states p on p.skill_id = s.skill_id
                left join skill_aliases a on a.skill_id = s.skill_id
                where lower(s.skill_id) = ?
                   or lower(s.name) = ?
                   or lower(s.slug) = ?
                   or lower(a.alias) = ?
                limit 1
                """,
                (normalized, normalized, normalized, normalized),
            ).fetchone()
            return dict(row) if row else None

    def upsert_review_item(self, item: ReviewItem, *, status: str = "pending") -> None:
        payload = item.model_dump(mode="json")
        with self.connect() as connection:
            connection.execute(
                """
                insert into review_queue (
                    item_id, reason, proposed_change_json, evidence_ids_json, risk_level, status
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(item_id) do update set
                    reason = excluded.reason,
                    proposed_change_json = excluded.proposed_change_json,
                    evidence_ids_json = excluded.evidence_ids_json,
                    risk_level = excluded.risk_level
                where review_queue.status = 'pending'
                """,
                (
                    payload["item_id"],
                    payload["reason"],
                    json.dumps(payload["proposed_change"], sort_keys=True),
                    json.dumps(payload["evidence_ids"], sort_keys=True),
                    payload["risk_level"],
                    status,
                ),
            )

    def list_review_items(self, *, include_closed: bool = False) -> list[dict[str, Any]]:
        query = "select * from review_queue"
        params: tuple[object, ...] = ()
        if not include_closed:
            query += " where status = 'pending'"
        query += " order by created_at, item_id"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_review_item(self, item_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("select * from review_queue where item_id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def set_review_status(self, item_id: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute("update review_queue set status = ? where item_id = ?", (status, item_id))

    def add_manual_override(self, *, target_type: str, target_id: str, action: str, payload: dict[str, Any]) -> None:
        override_id = f"{target_type}:{target_id}:{action}:{json.dumps(payload, sort_keys=True)}"
        with self.connect() as connection:
            connection.execute(
                """
                insert or ignore into manual_overrides (override_id, target_type, target_id, action, payload_json)
                values (?, ?, ?, ?, ?)
                """,
                (override_id, target_type, target_id, action, json.dumps(payload, sort_keys=True)),
            )

    def list_manual_overrides(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("select * from manual_overrides order by created_at, override_id").fetchall()
            return [dict(row) for row in rows]

    def sync_review_queue_file(self) -> Path:
        review_file = self.project_root / "state" / "review_queue.jsonl"
        lines: list[str] = []
        for row in self.list_review_items():
            lines.append(
                json.dumps(
                    {
                        "item_id": row["item_id"],
                        "reason": row["reason"],
                        "proposed_change": json.loads(row["proposed_change_json"]),
                        "evidence_ids": json.loads(row["evidence_ids_json"]),
                        "risk_level": row["risk_level"],
                        "status": row["status"],
                    },
                    sort_keys=True,
                )
            )
        review_file.write_text("\n".join(lines) + ("\n" if lines else ""))
        return review_file

    def merge_imported_records_from(self, source_db_path: Path) -> dict[str, int]:
        """Merge source-derived records from another Traccia catalog.

        The graph tables are intentionally excluded. A project graph is derived from
        evidence, so importing already-derived skills would split canonicalization
        decisions across model/project boundaries. Extraction checkpoints are also
        excluded because they are only safe inside the exact pipeline/model run that
        created them.
        """

        source_db_path = source_db_path.resolve()
        if not source_db_path.exists():
            raise FileNotFoundError(f"Source catalog not found: {source_db_path}")
        if source_db_path == self.db_path.resolve():
            raise ValueError("Cannot merge a catalog into itself")

        with self.connect() as connection:
            connection.execute("attach database ? as source_catalog", (str(source_db_path),))
            counts = {
                "sources": _insert_missing_rows(
                    connection,
                    table="sources",
                    columns=(
                        "source_id",
                        "uri",
                        "source_type",
                        "source_category",
                        "parser",
                        "sha256",
                        "created_at",
                        "ingested_at",
                        "title",
                        "language",
                        "sensitivity",
                        "metadata_json",
                        "status",
                    ),
                ),
                "source_spans": _insert_missing_rows(
                    connection,
                    table="source_spans",
                    columns=(
                        "span_id",
                        "source_id",
                        "span_start",
                        "span_end",
                        "label",
                        "content_hash",
                    ),
                ),
                "evidence_items": _insert_missing_rows(
                    connection,
                    table="evidence_items",
                    columns=(
                        "evidence_id",
                        "source_id",
                        "span_start",
                        "span_end",
                        "quote",
                        "evidence_type",
                        "reliability",
                        "extractor_version",
                        "confidence",
                        "payload_json",
                    ),
                ),
            }
        return counts


def _validate_sql_identifier(identifier: str) -> None:
    if not SQL_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Unsafe SQLite identifier: {identifier!r}")


def _insert_missing_rows(
    connection: sqlite3.Connection, *, table: str, columns: tuple[str, ...]
) -> int:
    _validate_sql_identifier(table)
    for column in columns:
        _validate_sql_identifier(column)
    column_list = ", ".join(columns)
    connection.execute(
        f"""
        insert or ignore into {table} ({column_list})
        select {column_list}
        from source_catalog.{table}
        """
    )
    return int(connection.execute("select changes()").fetchone()[0])
