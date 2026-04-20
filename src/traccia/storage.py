from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from traccia.models import (
    EvidenceItem,
    ParsedSpan,
    PersonSkillState,
    ReviewItem,
    SkillEdge,
    SkillNode,
    SourceDocument,
)


class Storage:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.db_path = project_root / "state" / "catalog.sqlite"

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            self._ensure_schema(connection)
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
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
            row = connection.execute(
                "select * from sources where source_id = ?", (source_id,)
            ).fetchone()
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

    def clear_pending_review_items(self) -> None:
        with self.connect() as connection:
            connection.execute("delete from review_queue where status = 'pending'")

    def upsert_source(self, source: SourceDocument) -> None:
        payload = source.model_dump(mode="json")
        with self.connect() as connection:
            connection.execute(
                """
                insert into sources (
                    source_id, uri, source_type, source_category,
                    parser, sha256, created_at, ingested_at,
                    title, language, sensitivity, metadata_json,
                    status
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
            for span in spans:
                connection.execute(
                    """
                    insert into source_spans (
                        span_id, source_id, span_start, span_end, label, content_hash
                    ) values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        span.span_id,
                        source_id,
                        span.span_start,
                        span.span_end,
                        span.segment_kind,
                        span.span_id,
                    ),
                )

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

    def list_evidence(self) -> list[EvidenceItem]:
        with self.connect() as connection:
            rows = connection.execute(
                "select payload_json from evidence_items order by evidence_id"
            ).fetchall()
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
                    insert into skills (
                        skill_id, kind, name, slug,
                        description, status, created_by, last_updated
                    )
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
                        skill_id, level, xp, confidence, core_self_centrality,
                        recency_score, breadth_score, depth_score, artifact_score,
                        teaching_score, first_seen_at, first_learned_at,
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
                       p.teaching_score, p.first_seen_at, p.first_learned_at,
                       p.first_strong_evidence_at, p.last_evidence_at,
                       p.last_strong_evidence_at, p.historical_peak_level,
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
                       p.teaching_score, p.first_seen_at, p.first_learned_at,
                       p.first_strong_evidence_at, p.last_evidence_at,
                       p.last_strong_evidence_at, p.historical_peak_level,
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
            row = connection.execute(
                "select * from review_queue where item_id = ?", (item_id,)
            ).fetchone()
            return dict(row) if row else None

    def set_review_status(self, item_id: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "update review_queue set status = ? where item_id = ?",
                (status, item_id),
            )

    def add_manual_override(
        self, *, target_type: str, target_id: str, action: str, payload: dict[str, Any],
    ) -> None:
        override_id = f"{target_type}:{target_id}:{action}:{json.dumps(payload, sort_keys=True)}"
        with self.connect() as connection:
            connection.execute(
                """
                insert or ignore into manual_overrides (
                    override_id, target_type, target_id, action, payload_json
                )
                values (?, ?, ?, ?, ?)
                """,
                (override_id, target_type, target_id, action, json.dumps(payload, sort_keys=True)),
            )

    def list_manual_overrides(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "select * from manual_overrides order by created_at, override_id"
            ).fetchall()
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
