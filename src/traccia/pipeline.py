from __future__ import annotations

import json
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from traccia.config import load_config
from traccia.llm import CanonicalizationRequest, ScoringRequest, backend_from_config, load_prompt
from traccia.models import (
    EvidenceItem,
    FreshnessState,
    NodeStatus,
    PersonSkillState,
    PersonSkillStatus,
    ReviewItem,
    ReviewRiskLevel,
    SkillEdge,
    SkillKind,
    SkillNode,
)
from traccia.parsers import parse_document, supported_file
from traccia.pipeline_support import build_skill_node, support_score
from traccia.rendering import render_project
from traccia.storage import Storage
from traccia.taxonomy import DOMAINS
from traccia.utils import iso_now, short_hash, skill_id, slugify, source_id_for_relative_path


@dataclass(slots=True)
class BatchResult:
    processed: int = 0
    skipped: int = 0
    imported: int = 0
    deleted: int = 0


class Pipeline:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.storage = Storage(self.project_root)
        self.config = load_config(self.project_root / "config" / "config.yaml")
        self.backend = backend_from_config(self.config)

    def add_file(self, path: Path) -> Path:
        imported_path = self._import_path_for(path=path, root=path.parent)
        imported_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, imported_path)
        return imported_path

    def add_directory(self, root: Path) -> int:
        count = 0
        for path in self._discover_files(root):
            self.add_file(path)
            count += 1
        return count

    def ingest_file(self, path: Path, *, root: Path | None = None, force: bool = False) -> tuple[str, bool]:
        imported_path = self._import_external_source(path=path, root=root or path.parent)
        relative_import_path = imported_path.relative_to(self.project_root / "raw" / "imported")
        parsed_document = parse_document(imported_path, project_relative_path=relative_import_path)
        previous_source = self.storage.fetch_source(parsed_document.source.source_id)
        if previous_source and previous_source["sha256"] == parsed_document.source.sha256 and not force:
            return parsed_document.source.source_id, False

        self.storage.upsert_source(parsed_document.source)
        self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
        self._write_parsed_artifact(parsed_document)

        evidence_items = self.backend.extract_evidence(
            prompt=load_prompt(self.project_root, "extract_evidence.md"),
            document=parsed_document,
        )
        self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
        self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
        return parsed_document.source.source_id, True

    def ingest_directory(self, root: Path, *, force: bool = False) -> BatchResult:
        result = BatchResult()
        files = self._discover_files(root)
        result.deleted = self._sync_import_scope(root=root, current_files=files)
        for path in files:
            _, processed = self.ingest_file(path, root=root, force=force)
            result.imported += 1
            if processed:
                result.processed += 1
            else:
                result.skipped += 1
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        self._append_log(
            f"- {iso_now()}: ingest-dir root={root.resolve()} imported={result.imported} processed={result.processed} skipped={result.skipped} deleted={result.deleted}"
        )
        return result

    def reingest(self, source_id: str, *, force: bool = True) -> bool:
        source_row = self.storage.fetch_source(source_id)
        if not source_row:
            raise ValueError(f"Unknown source_id: {source_id}")
        source_path = Path(source_row["uri"].replace("file://", ""))
        _, processed = self.ingest_file(source_path, root=source_path.parent, force=force)
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        return processed

    def rebuild(self) -> BatchResult:
        result = BatchResult()
        imported_root = self.project_root / "raw" / "imported"
        for path in self._discover_files(imported_root):
            relative_import_path = path.relative_to(imported_root)
            parsed_document = parse_document(path, project_relative_path=relative_import_path)
            self.storage.upsert_source(parsed_document.source)
            self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
            self._write_parsed_artifact(parsed_document)
            evidence_items = self.backend.extract_evidence(
                prompt=load_prompt(self.project_root, "extract_evidence.md"),
                document=parsed_document,
            )
            self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
            self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
            result.processed += 1
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        self._append_log(f"- {iso_now()}: rebuild processed={result.processed}")
        return result

    def watch(self, root: Path, *, interval_seconds: int = 2) -> None:
        last_seen: dict[str, str] = {}
        while True:
            changed = False
            for path in self._discover_files(root):
                current_stamp = f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
                if last_seen.get(str(path)) != current_stamp:
                    last_seen[str(path)] = current_stamp
                    changed = True
            if changed:
                self.ingest_directory(root)
            time.sleep(interval_seconds)

    def recompute_graph(self) -> None:
        evidence_items = self.storage.list_evidence()
        overrides = self.storage.list_manual_overrides()
        self.storage.clear_pending_review_items()
        review_status_by_id = {
            row["item_id"]: row["status"]
            for row in self.storage.list_review_items(include_closed=True)
            if row["status"] != "pending"
        }
        existing_skill_rows = self.storage.list_skill_rows()
        previous_skill_rows = {
            str(row["skill_id"]): row for row in existing_skill_rows if row["kind"] != "domain"
        }

        support: dict[str, dict[str, object]] = {}
        for evidence_item in evidence_items:
            for candidate in evidence_item.skill_candidates:
                bucket = support.setdefault(candidate, {"evidence": []})
                bucket["evidence"].append(evidence_item)

        manual_skills: set[str] = set()
        alias_overrides: dict[str, set[str]] = defaultdict(set)
        locked_skills: set[str] = set()
        hidden_skills: set[str] = set()
        for override in overrides:
            payload = json.loads(override["payload_json"])
            if override["action"] == "create_skill":
                manual_skills.add(payload["name"])
            elif override["action"] == "alias_add":
                alias_overrides[override["target_id"]].add(payload["alias"])
            elif override["action"] == "lock":
                locked_skills.add(override["target_id"])
            elif override["action"] == "hide":
                hidden_skills.add(override["target_id"])

        skills: list[SkillNode] = []
        states: list[PersonSkillState] = []
        edges: list[SkillEdge] = []
        created_names: set[str] = set()

        for domain in DOMAINS:
            skills.append(
                SkillNode(
                    skill_id=skill_id("domain", domain.name),
                    kind=SkillKind.DOMAIN,
                    name=domain.name,
                    slug=slugify(domain.name),
                    aliases=[],
                    description=domain.description,
                    taxonomy_refs=[],
                    status=NodeStatus.ACTIVE,
                    created_by="system",
                    last_updated=iso_now(),
                )
            )

        for candidate_name, candidate_support in sorted(support.items()):
            decision = self.backend.canonicalize(
                prompt=load_prompt(self.project_root, "canonicalize_skills.md"),
                request=CanonicalizationRequest(
                    candidate_name=candidate_name,
                    evidence_items=list(candidate_support["evidence"]),
                    existing_skills=existing_skill_rows,
                    thresholds={
                        "strong_evidence_auto_create": self.config.thresholds.strong_evidence_auto_create,
                        "review_confidence_floor": self.config.thresholds.review_confidence_floor,
                        "consumption_max_level": self.config.thresholds.consumption_max_level,
                    },
                ),
            )

            if candidate_name in manual_skills and decision.action in {"ignore", "review"}:
                decision.action = "create"
                decision.canonical_name = candidate_name

            if decision.action == "ignore":
                continue

            if decision.action == "review":
                item_id = f"review_{slugify(candidate_name)}"
                if review_status_by_id.get(item_id) not in {"accepted", "rejected"}:
                    self.storage.upsert_review_item(
                        ReviewItem(
                            item_id=item_id,
                            reason=decision.reason,
                            proposed_change={"type": "create_skill", "name": candidate_name},
                            evidence_ids=[item.evidence_id for item in candidate_support["evidence"]],
                            risk_level=ReviewRiskLevel(decision.review_risk_level),
                        )
                    )
                continue

            canonical_name = decision.canonical_name or candidate_name
            skill = build_skill_node(canonical_name)
            skill.aliases.extend(sorted(alias_overrides.get(skill.skill_id, set())))
            skill.aliases.extend(
                sorted(alias for alias in decision.aliases if alias not in skill.aliases)
            )
            if skill.skill_id in hidden_skills:
                skill.status = NodeStatus.HIDDEN
            skills.append(skill)
            created_names.add(canonical_name)

            score_payload = self.backend.score_skill(
                prompt=load_prompt(self.project_root, "score_skill_state.md"),
                request=ScoringRequest(
                    skill=skill,
                    evidence_items=list(candidate_support["evidence"]),
                    thresholds={"consumption_max_level": self.config.thresholds.consumption_max_level},
                    locked=skill.skill_id in locked_skills,
                    hidden=skill.skill_id in hidden_skills,
                ),
            )
            states.append(
                _build_person_skill_state(
                    skill_id=skill.skill_id,
                    evidence_items=list(candidate_support["evidence"]),
                    score_payload=score_payload,
                    previous_row=previous_skill_rows.get(skill.skill_id),
                    locked=skill.skill_id in locked_skills,
                )
            )

            if skill.description and "::" in skill.description:
                domain_name = skill.description.split("::", maxsplit=1)[0]
                edges.append(
                    SkillEdge(
                        edge_id=f"edge_{short_hash(f'{domain_name}:{skill.skill_id}', length=10)}",
                        from_skill_id=skill_id("domain", domain_name),
                        to_skill_id=skill.skill_id,
                        edge_type="parent_of",
                        weight=1.0,
                        source="taxonomy",
                        confidence=1.0,
                    )
                )

        for item_id, status in review_status_by_id.items():
            if status == "pending":
                continue
            item = self.storage.get_review_item(item_id)
            if not item:
                continue
            proposed = json.loads(item["proposed_change_json"])
            name = proposed.get("name")
            if item["status"] == "accepted" and name and name not in created_names:
                skill = build_skill_node(name)
                skills.append(skill)
                created_names.add(name)
                states.append(
                    PersonSkillState(
                        skill_id=skill.skill_id,
                        level=1,
                        xp=12.0,
                        confidence=0.35,
                        core_self_centrality=0.2,
                        recency_score=0.6,
                        breadth_score=0.2,
                        depth_score=0.2,
                        artifact_score=0.0,
                        teaching_score=0.0,
                        first_seen_at=datetime.now(tz=UTC),
                        first_learned_at=None,
                        first_strong_evidence_at=datetime.now(tz=UTC),
                        last_evidence_at=datetime.now(tz=UTC),
                        last_strong_evidence_at=datetime.now(tz=UTC),
                        historical_peak_level=1,
                        historical_peak_at=datetime.now(tz=UTC),
                        acquired_at=datetime.now(tz=UTC),
                        acquisition_basis="manual_review_accept",
                        freshness=FreshnessState.ACTIVE,
                        status=PersonSkillStatus.MANUAL,
                        locked=False,
                        manual_note="Accepted from review queue.",
                    )
                )

        self.storage.replace_graph(skills=skills, states=states, edges=edges)
        self.storage.sync_review_queue_file()

    def _discover_files(self, root: Path) -> list[Path]:
        return [path for path in sorted(root.rglob("*")) if path.is_file() and supported_file(path)]

    def _sync_import_scope(self, *, root: Path, current_files: list[Path]) -> int:
        current_source_ids = {
            source_id_for_relative_path(self._relative_import_path_for(path=path, root=root))
            for path in current_files
        }
        deleted = 0
        scope_root = (self.project_root / "raw" / "imported" / slugify(root.name or "imported")).resolve()
        for source_row in self.storage.list_sources():
            if source_row["status"] == "deleted":
                continue
            source_uri = str(source_row["uri"])
            if not source_uri.startswith("file://"):
                continue
            source_path = Path(source_uri.replace("file://", "")).resolve()
            if not _path_within_scope(source_path, scope_root):
                continue
            if source_row["source_id"] in current_source_ids:
                continue
            self.storage.mark_source_deleted(str(source_row["source_id"]))
            self.storage.delete_source_derived_records(str(source_row["source_id"]))
            self._delete_source_artifacts(str(source_row["source_id"]), source_path)
            deleted += 1
        return deleted

    def _import_external_source(self, *, path: Path, root: Path) -> Path:
        destination = self._import_path_for(path=path, root=root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        return destination

    def _import_path_for(self, *, path: Path, root: Path) -> Path:
        return self.project_root / "raw" / "imported" / self._relative_import_path_for(path=path, root=root)

    def _relative_import_path_for(self, *, path: Path, root: Path) -> Path:
        root_name = slugify(root.name or "imported")
        return Path(root_name) / path.relative_to(root)

    def _delete_source_artifacts(self, source_id: str, imported_path: Path) -> None:
        parsed_artifact = self.project_root / "parsed" / f"{source_id}.json"
        evidence_artifact = self.project_root / "evidence" / f"{source_id}.json"
        for artifact_path in (parsed_artifact, evidence_artifact, imported_path):
            if artifact_path.exists():
                artifact_path.unlink()

    def _write_parsed_artifact(self, parsed_document) -> None:
        artifact_path = self.project_root / "parsed" / f"{parsed_document.source.source_id}.json"
        artifact_path.write_text(parsed_document.model_dump_json(indent=2) + "\n")

    def _write_evidence_artifact(self, source_id: str, evidence_items: list[EvidenceItem]) -> None:
        artifact_path = self.project_root / "evidence" / f"{source_id}.json"
        artifact_path.write_text(
            json.dumps([item.model_dump(mode="json") for item in evidence_items], indent=2) + "\n"
        )

    def _append_log(self, line: str) -> None:
        log_path = self.project_root / "tree" / "log.md"
        with log_path.open("a", encoding="utf-8") as handle:
            if log_path.stat().st_size == 0:
                handle.write("# Ingest Log\n")
            handle.write(f"{line}\n")


def _latest_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    values = [item.time_reference for item in evidence_items if item.time_reference]
    if not values:
        return None
    latest = max(values)
    return _time_reference_to_datetime(latest)


def _earliest_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    values = [item.time_reference for item in evidence_items if item.time_reference]
    if not values:
        return None
    earliest = min(values)
    return _time_reference_to_datetime(earliest)


def _earliest_learning_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    learning_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value in {"studied", "researched", "passed_assessment"}
    ]
    if not learning_values:
        return None
    earliest = min(learning_values)
    return _time_reference_to_datetime(earliest)


def _latest_strong_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    strong_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value not in {"mentioned", "self_claimed", "studied", "researched"}
    ]
    if not strong_values:
        return None
    latest = max(strong_values)
    return _time_reference_to_datetime(latest)


def _earliest_strong_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    strong_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value not in {"mentioned", "self_claimed", "studied", "researched"}
    ]
    if not strong_values:
        return None
    earliest = min(strong_values)
    return _time_reference_to_datetime(earliest)


def _freshness_from_evidence(
    evidence_items: list[EvidenceItem],
) -> tuple[float, FreshnessState]:
    reference_time = _latest_strong_evidence_at(evidence_items) or _latest_evidence_at(evidence_items)
    if not reference_time:
        return 0.0, FreshnessState.HISTORICAL

    age_days = max(0, (datetime.now(tz=UTC) - reference_time).days)
    if age_days <= 90:
        return 1.0, FreshnessState.ACTIVE
    if age_days <= 180:
        return 0.7, FreshnessState.WARMING
    if age_days <= 365:
        return 0.4, FreshnessState.STALE
    return 0.15, FreshnessState.HISTORICAL


def _build_person_skill_state(
    *,
    skill_id: str,
    evidence_items: list[EvidenceItem],
    score_payload,
    previous_row: dict[str, object] | None,
    locked: bool,
) -> PersonSkillState:
    current_first_seen_at = _earliest_evidence_at(evidence_items)
    current_first_learned_at = _earliest_learning_evidence_at(evidence_items)
    current_first_strong_evidence_at = _earliest_strong_evidence_at(evidence_items)
    last_evidence_at = _latest_evidence_at(evidence_items)
    last_strong_evidence_at = _latest_strong_evidence_at(evidence_items)
    recency_score, freshness = _freshness_from_evidence(evidence_items)

    previous_first_seen_at = _row_datetime(previous_row, "first_seen_at")
    previous_first_learned_at = _row_datetime(previous_row, "first_learned_at")
    previous_first_strong_evidence_at = _row_datetime(previous_row, "first_strong_evidence_at")

    first_seen_at = _merge_earliest_datetime(current_first_seen_at, previous_first_seen_at)
    first_learned_at = _merge_earliest_datetime(current_first_learned_at, previous_first_learned_at)
    first_strong_evidence_at = (
        _merge_earliest_datetime(current_first_strong_evidence_at, previous_first_strong_evidence_at)
        if current_first_strong_evidence_at or previous_first_strong_evidence_at
        else None
    )
    acquired_at, acquisition_basis = _estimate_acquired_at(
        first_seen_at=first_seen_at,
        first_learned_at=first_learned_at,
        first_strong_evidence_at=first_strong_evidence_at,
        previous_acquired_at=_row_datetime(previous_row, "acquired_at"),
        previous_acquisition_basis=str(previous_row["acquisition_basis"]) if previous_row and previous_row.get("acquisition_basis") else None,
    )

    current_level = int(score_payload.level)
    previous_peak_level = max(
        int(previous_row["historical_peak_level"] or 0) if previous_row else 0,
        int(previous_row["level"] or 0) if previous_row else 0,
    )
    historical_peak_level = max(current_level, previous_peak_level)

    previous_peak_at = _row_datetime(previous_row, "historical_peak_at")
    if historical_peak_level > previous_peak_level:
        historical_peak_at = last_strong_evidence_at or last_evidence_at or datetime.now(tz=UTC)
    elif previous_peak_at:
        historical_peak_at = previous_peak_at
    else:
        historical_peak_at = _row_datetime(previous_row, "last_strong_evidence_at") or _row_datetime(
            previous_row, "last_evidence_at"
        )

    return PersonSkillState(
        skill_id=skill_id,
        level=current_level,
        xp=round(sum(support_score(item) for item in evidence_items) * 100, 2),
        confidence=score_payload.confidence,
        core_self_centrality=_core_self_centrality(
            evidence_items=evidence_items,
            first_seen_at=first_seen_at,
            last_evidence_at=last_evidence_at,
        ),
        recency_score=recency_score,
        breadth_score=score_payload.breadth_score,
        depth_score=score_payload.depth_score,
        artifact_score=score_payload.artifact_score,
        teaching_score=score_payload.teaching_score,
        first_seen_at=first_seen_at,
        first_learned_at=first_learned_at,
        first_strong_evidence_at=first_strong_evidence_at,
        last_evidence_at=last_evidence_at,
        last_strong_evidence_at=last_strong_evidence_at,
        historical_peak_level=historical_peak_level,
        historical_peak_at=historical_peak_at,
        acquired_at=acquired_at,
        acquisition_basis=acquisition_basis,
        freshness=freshness,
        status=PersonSkillStatus(score_payload.status),
        locked=locked,
        manual_note=score_payload.manual_note,
    )


def _row_datetime(row: dict[str, object] | None, key: str) -> datetime | None:
    if not row or not row.get(key):
        return None
    raw_value = str(row[key])
    if raw_value.endswith("Z"):
        raw_value = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw_value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _core_self_centrality(
    *,
    evidence_items: list[EvidenceItem],
    first_seen_at: datetime | None,
    last_evidence_at: datetime | None,
) -> float:
    if not evidence_items:
        return 0.0

    unique_sources = len({item.source_id for item in evidence_items})
    unique_evidence_types = len({item.evidence_type.value for item in evidence_items})
    artifact_backed_count = sum(
        1
        for item in evidence_items
        if item.evidence_type.value in {"implemented", "debugged", "designed", "presented", "taught", "reviewed"}
    )

    duration_score = 0.0
    if first_seen_at and last_evidence_at:
        duration_days = max(0, (last_evidence_at - first_seen_at).days)
        duration_score = min(1.0, duration_days / 365)

    recurrence_score = min(1.0, unique_sources / 4)
    variety_score = min(1.0, unique_evidence_types / 5)
    artifact_score = min(1.0, artifact_backed_count / 4)

    centrality = (
        (duration_score * 0.35)
        + (recurrence_score * 0.3)
        + (variety_score * 0.15)
        + (artifact_score * 0.2)
    )
    return round(min(1.0, centrality), 2)


def _path_within_scope(path: Path, scope_root: Path) -> bool:
    try:
        path.relative_to(scope_root)
        return True
    except ValueError:
        return False


def _merge_earliest_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left and right:
        return min(left, right)
    return left or right


def _time_reference_to_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _estimate_acquired_at(
    *,
    first_seen_at: datetime | None,
    first_learned_at: datetime | None,
    first_strong_evidence_at: datetime | None,
    previous_acquired_at: datetime | None,
    previous_acquisition_basis: str | None,
) -> tuple[datetime | None, str | None]:
    if first_strong_evidence_at:
        return first_strong_evidence_at, "strong_evidence"
    if first_learned_at:
        return first_learned_at, "learning_evidence"
    if first_seen_at:
        return first_seen_at, "first_observed"
    return previous_acquired_at, previous_acquisition_basis
