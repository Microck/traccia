from __future__ import annotations

import json
import shutil
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from traccia.config import load_config
from traccia.llm import (
    CanonicalizationRequest,
    LLMBackend,
    ScoringRequest,
    backend_from_config,
    load_prompt,
)
from traccia.models import (
    EvidenceItem,
    FreshnessState,
    IngestManifest,
    IngestManifestEntry,
    IngestMaterialStatus,
    NodeStatus,
    ParsedDocument,
    ParsedSpan,
    PersonSkillState,
    PersonSkillStatus,
    ReviewItem,
    ReviewRiskLevel,
    SkillEdge,
    SkillKind,
    SkillNode,
    SourceFamily,
)
from traccia.parsers import ingestable_file, parse_document, sniff_text_bytes
from traccia.pipeline_support import build_skill_node, support_score
from traccia.rendering import render_project
from traccia.source_detection import (
    FamilyDetection,
    detect_source_family_from_archive,
    detect_source_family_from_path,
    refine_archive_member_detection,
)
from traccia.storage import Storage
from traccia.taxonomy import DOMAINS
from traccia.utils import (
    iso_now,
    short_hash,
    skill_id,
    slugify,
    source_id_for_relative_path,
)


@dataclass(slots=True)
class BatchResult:
    discovered: int = 0
    processed: int = 0
    skipped: int = 0
    imported: int = 0
    deleted: int = 0
    failed: int = 0

@dataclass(slots=True)
class DiscoverySummary:
    total_materials: int = 0
    direct_files: int = 0
    archive_members: int = 0
    by_root: dict[str, int] = field(default_factory=dict)
    by_family: dict[str, int] = field(default_factory=dict)
    by_family_subproduct: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ImportMaterial:
    source_path: Path
    relative_import_path: Path
    source_family: SourceFamily
    source_family_subproduct: str | None
    detection_reason: str
    archive_member: str | None = None


ARCHIVE_SUFFIXES = {".zip"}
# Small span batches are materially more stable across OpenAI-compatible proxies
# than large document chunks when running long export ingests.
MAX_EXTRACTION_SPANS = 6
MAX_EXTRACTION_CHARACTERS = 12_000


class Pipeline:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.storage = Storage(self.project_root)
        self.config = load_config(self.project_root / "config" / "config.yaml")
        self._backend: LLMBackend | None = None

    @property
    def backend(self) -> LLMBackend:
        if self._backend is None:
            self._backend = backend_from_config(self.config)
        return self._backend

    @backend.setter
    def backend(self, value: LLMBackend) -> None:
        self._backend = value

    def add_file(self, path: Path) -> Path:
        materials = self._materials_for_path(path=path, root=path.parent)
        if not materials:
            raise ValueError(f"No ingestable material found in {path}")
        imported_paths = [self._import_material(material) for material in materials]
        if len(imported_paths) == 1:
            return imported_paths[0]
        return imported_paths[0].parent

    def add_directory(self, root: Path) -> int:
        materials = self._discover_materials(root)
        for material in materials:
            self._import_material(material)
        return len(materials)

    def discover_directory(self, root: Path) -> DiscoverySummary:
        materials = self._discover_materials(root)
        return self._summarize_materials(materials)

    def ingest_file(self, path: Path, *, root: Path | None = None, force: bool = False) -> tuple[str, bool]:
        materials = self._materials_for_path(path=path, root=root or path.parent)
        if not materials:
            raise ValueError(f"No ingestable material found in {path}")

        processed_any = False
        first_source_id: str | None = None
        manifest_entries: list[IngestManifestEntry] = []
        for material in materials:
            source_id, processed = self._ingest_material(material, force=force)
            if first_source_id is None:
                first_source_id = source_id
            processed_any = processed_any or processed
            manifest_entries.append(
                IngestManifestEntry(
                    relative_import_path=material.relative_import_path.as_posix(),
                    source_path=material.source_path.resolve().as_posix(),
                    archive_member=material.archive_member,
                    source_family=material.source_family,
                    source_family_subproduct=material.source_family_subproduct,
                    detection_reason=material.detection_reason,
                    status=IngestMaterialStatus.PROCESSED if processed else IngestMaterialStatus.SKIPPED,
                    source_id=source_id,
                )
            )
        self._write_ingest_manifest(root=root or path.parent, entries=manifest_entries)
        fallback_source_id = source_id_for_relative_path(
            self._relative_import_path_for(path=path, root=root or path.parent)
        )
        return first_source_id or fallback_source_id, processed_any

    def ingest_directory(self, root: Path, *, force: bool = False) -> BatchResult:
        result = BatchResult()
        manifest_entries: dict[str, IngestManifestEntry] = {}
        current_materials = self._discover_materials(root)
        discovery = self._summarize_materials(current_materials)
        result.discovered = discovery.total_materials
        total_materials = len(current_materials)

        self._append_log(
            (
                f"- {iso_now()}: ingest-discovered root={root.resolve()} "
                f"materials={discovery.total_materials} direct_files={discovery.direct_files} "
                f"archive_members={discovery.archive_members} "
                f"by_root={_format_counts(discovery.by_root)} "
                f"by_family={_format_counts(discovery.by_family)} "
                f"by_family_subproduct={_format_counts(discovery.by_family_subproduct)}"
            )
        )
        self._write_progress(
            status="running",
            root=root,
            result=result,
            discovery=discovery,
            total_materials=total_materials,
        )

        for index, material in enumerate(current_materials, start=1):
            entry = manifest_entries.setdefault(
                material.relative_import_path.as_posix(),
                IngestManifestEntry(
                    relative_import_path=material.relative_import_path.as_posix(),
                    source_path=material.source_path.resolve().as_posix(),
                    archive_member=material.archive_member,
                    source_family=material.source_family,
                    source_family_subproduct=material.source_family_subproduct,
                    detection_reason=material.detection_reason,
                    status=IngestMaterialStatus.DISCOVERED,
                ),
            )
            entry = manifest_entries[material.relative_import_path.as_posix()]
            self._append_log(
                " ".join(
                    [
                        f"- {iso_now()}: material-start",
                        f"index={index}/{total_materials}",
                        f"relative_import_path={material.relative_import_path.as_posix()}",
                        f"family={material.source_family.value}",
                        f"subproduct={material.source_family_subproduct or '-'}",
                        f"archive_member={material.archive_member or '-'}",
                    ]
                )
            )
            self._write_progress(
                status="running",
                root=root,
                result=result,
                discovery=discovery,
                total_materials=total_materials,
                current_index=index,
                current_material=material,
            )
            try:
                source_id, processed = self._ingest_material(material, force=force)
            except Exception as exc:
                result.failed += 1
                entry.status = IngestMaterialStatus.FAILED
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: material-failed",
                            f"index={index}/{total_materials}",
                            f"path={material.source_path.resolve()}",
                            f"relative_import_path={material.relative_import_path.as_posix()}",
                            f"error={type(exc).__name__}:{exc}",
                        ]
                    )
                )
                self._write_progress(
                    status="running",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=index,
                    current_material=material,
                )
                continue

            result.imported += 1
            entry.source_id = source_id
            if processed:
                result.processed += 1
                entry.status = IngestMaterialStatus.PROCESSED
            else:
                result.skipped += 1
                entry.status = IngestMaterialStatus.SKIPPED
            self._append_log(
                " ".join(
                    [
                        f"- {iso_now()}: material-finished",
                        f"index={index}/{total_materials}",
                        f"source_id={source_id}",
                        f"status={entry.status.value}",
                        f"relative_import_path={material.relative_import_path.as_posix()}",
                    ]
                )
            )
            self._write_progress(
                status="running",
                root=root,
                result=result,
                discovery=discovery,
                total_materials=total_materials,
                current_index=index,
                current_material=material,
            )
        result.deleted = self._sync_import_scope(root=root, current_materials=current_materials)
        self._write_ingest_manifest(root=root, entries=list(manifest_entries.values()))
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        self._append_log(
            (
                f"- {iso_now()}: ingest-dir root={root.resolve()} imported={result.imported} "
                f"processed={result.processed} skipped={result.skipped} failed={result.failed} "
                f"deleted={result.deleted}"
            )
        )
        self._write_progress(
            status="completed",
            root=root,
            result=result,
            discovery=discovery,
            total_materials=total_materials,
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
            self._rebuild_imported_path(path=path, relative_import_path=relative_import_path)
            result.processed += 1
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        self._append_log(f"- {iso_now()}: rebuild processed={result.processed}")
        return result

    def watch(self, root: Path, *, interval_seconds: int = 2) -> None:
        last_seen: dict[str, str] = {}
        while True:
            changed = False
            for path in self._watch_roots(root):
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
        return [path for path in sorted(root.rglob("*")) if path.is_file() and ingestable_file(path)]

    def _watch_roots(self, root: Path) -> list[Path]:
        return [
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and (ingestable_file(path) or self._is_archive(path))
        ]

    def _discover_materials(self, root: Path) -> list[ImportMaterial]:
        return list(self._iter_materials(root))

    def _iter_materials(self, root: Path) -> Iterator[ImportMaterial]:
        seen_relative_paths: set[Path] = set()
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if not (ingestable_file(path) or self._is_archive(path)):
                continue
            for material in self._materials_for_path(path=path, root=root):
                if material.relative_import_path in seen_relative_paths:
                    continue
                seen_relative_paths.add(material.relative_import_path)
                yield material

    def _materials_for_path(self, *, path: Path, root: Path) -> list[ImportMaterial]:
        if self._is_archive(path):
            return self._archive_materials(path=path, root=root)
        if ingestable_file(path):
            detection = detect_source_family_from_path(path.relative_to(root))
            return [
                ImportMaterial(
                    source_path=path,
                    relative_import_path=self._relative_import_path_for(path=path, root=root),
                    source_family=detection.source_family,
                    source_family_subproduct=detection.subproduct,
                    detection_reason=detection.reason,
                )
            ]
        return []

    def _archive_materials(self, *, path: Path, root: Path) -> list[ImportMaterial]:
        materials: list[ImportMaterial] = []
        archive_root = self._archive_relative_root(path=path, root=root)
        detection = detect_source_family_from_archive(path)
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member_path = Path(info.filename)
                if self._unsafe_archive_member(member_path):
                    continue
                if not self._ingestable_archive_member(archive=archive, info=info):
                    continue
                member_detection = refine_archive_member_detection(
                    archive_detection=detection,
                    member_path=member_path,
                )
                materials.append(
                    ImportMaterial(
                        source_path=path,
                        relative_import_path=archive_root / member_path,
                        source_family=member_detection.source_family,
                        source_family_subproduct=member_detection.subproduct,
                        detection_reason=member_detection.reason,
                        archive_member=info.filename,
                    )
                )
        return materials

    def _sync_import_scope(self, *, root: Path, current_materials: list[ImportMaterial]) -> int:
        current_source_ids = {
            source_id_for_relative_path(material.relative_import_path) for material in current_materials
        }
        deleted = 0
        scope_root = (self.project_root / "raw" / "imported" / slugify(root.name or "imported")).absolute()
        for source_row in self.storage.list_sources():
            if source_row["status"] == "deleted":
                continue
            metadata = json.loads(str(source_row["metadata_json"] or "{}"))
            relative_import_path = metadata.get("relative_import_path")
            if not isinstance(relative_import_path, str) or not relative_import_path:
                continue
            imported_path = (self.project_root / "raw" / "imported" / relative_import_path).absolute()
            if not _path_within_scope(imported_path, scope_root):
                continue
            if source_row["source_id"] in current_source_ids:
                continue
            self.storage.mark_source_deleted(str(source_row["source_id"]))
            self.storage.delete_source_derived_records(str(source_row["source_id"]))
            self._delete_source_artifacts(str(source_row["source_id"]), imported_path)
            deleted += 1
        return deleted

    def _ingest_material(self, material: ImportMaterial, *, force: bool) -> tuple[str, bool]:
        imported_path = self._import_material(material)
        parsed_document = self._parsed_document_for_material(material=material, imported_path=imported_path)
        previous_source = self.storage.fetch_source(parsed_document.source.source_id)
        if (
            previous_source
            and previous_source["sha256"] == parsed_document.source.sha256
            and self._ingest_artifacts_complete(parsed_document.source.source_id)
            and not force
        ):
            return parsed_document.source.source_id, False

        self.storage.upsert_source(parsed_document.source)
        self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
        self._write_parsed_artifact(parsed_document)

        evidence_items = self._extract_evidence_items(parsed_document, force=force)
        self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
        self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
        self.storage.clear_extraction_checkpoints(parsed_document.source.source_id)
        return parsed_document.source.source_id, True

    def _ingest_artifacts_complete(self, source_id: str) -> bool:
        parsed_artifact = self.project_root / "parsed" / f"{source_id}.json"
        evidence_artifact = self.project_root / "evidence" / f"{source_id}.json"
        return parsed_artifact.exists() and evidence_artifact.exists()

    def _rebuild_imported_path(self, *, path: Path, relative_import_path: Path) -> None:
        detection = detect_source_family_from_path(relative_import_path)
        parsed_document = self._annotate_parsed_document(
            parse_document(
                path,
                project_relative_path=relative_import_path,
                config=self.config,
                source_family=detection.source_family,
                source_family_subproduct=detection.subproduct,
            ),
            detection=detection,
            archive_member=None,
        )
        self.storage.upsert_source(parsed_document.source)
        self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
        self._write_parsed_artifact(parsed_document)
        evidence_items = self._extract_evidence_items(parsed_document, force=True)
        self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
        self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
        self.storage.clear_extraction_checkpoints(parsed_document.source.source_id)

    def _extract_evidence_items(
        self,
        parsed_document: ParsedDocument,
        *,
        force: bool = False,
    ) -> list[EvidenceItem]:
        evidence_items: list[EvidenceItem] = []
        prompt = load_prompt(self.project_root, "extract_evidence.md")
        chunks = _chunk_document(parsed_document)
        completed_chunks = self._resume_checkpoints_for_document(
            parsed_document=parsed_document,
            chunks=chunks,
            force=force,
        )

        if completed_chunks:
            self._append_log(
                (
                    f"- {iso_now()}: extraction-resume source_id={parsed_document.source.source_id} "
                    f"completed_chunks={len(completed_chunks)}/{len(chunks)}"
                )
            )

        for chunk_index, chunk in enumerate(chunks):
            resumed_evidence = completed_chunks.get(chunk_index)
            if resumed_evidence is not None:
                evidence_items.extend(resumed_evidence)
                continue

            chunk_evidence = self.backend.extract_evidence(
                prompt=prompt,
                document=chunk,
            )
            self.storage.upsert_extraction_checkpoint(
                source_id=parsed_document.source.source_id,
                source_sha256=parsed_document.source.sha256,
                extractor_version=self.config.pipeline.extractor_version,
                chunk_index=chunk_index,
                chunk_fingerprint=_chunk_fingerprint(chunk),
                evidence_items=chunk_evidence,
            )
            evidence_items.extend(chunk_evidence)
        return _normalize_evidence_items(parsed_document.source.source_id, evidence_items)

    def _resume_checkpoints_for_document(
        self,
        *,
        parsed_document: ParsedDocument,
        chunks: list[ParsedDocument],
        force: bool,
    ) -> dict[int, list[EvidenceItem]]:
        source_id = parsed_document.source.source_id
        if force:
            self.storage.clear_extraction_checkpoints(source_id)
            return {}

        rows = self.storage.list_extraction_checkpoints(source_id)
        if not rows:
            return {}

        expected_fingerprints = {
            chunk_index: _chunk_fingerprint(chunk) for chunk_index, chunk in enumerate(chunks)
        }
        resumed: dict[int, list[EvidenceItem]] = {}
        for row in rows:
            chunk_index = int(row["chunk_index"])
            if (
                row["source_sha256"] != parsed_document.source.sha256
                or row["extractor_version"] != self.config.pipeline.extractor_version
                or expected_fingerprints.get(chunk_index) != row["chunk_fingerprint"]
            ):
                self.storage.clear_extraction_checkpoints(source_id)
                return {}
            resumed[chunk_index] = [
                EvidenceItem.model_validate(item)
                for item in json.loads(str(row["evidence_json"]))
            ]
        return resumed

    def _import_material(self, material: ImportMaterial) -> Path:
        destination = self.project_root / "raw" / "imported" / material.relative_import_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if material.archive_member:
            with zipfile.ZipFile(material.source_path) as archive:
                with archive.open(material.archive_member) as source_handle:
                    with destination.open("wb") as destination_handle:
                        shutil.copyfileobj(source_handle, destination_handle)
        else:
            target_path = material.source_path.resolve()
            if destination.is_symlink():
                if destination.resolve() == target_path:
                    return destination
                destination.unlink()
            elif destination.exists():
                destination.unlink()
            destination.symlink_to(target_path)
        return destination

    def _parsed_document_for_material(self, *, material: ImportMaterial, imported_path: Path) -> ParsedDocument:
        parsed_document = parse_document(
            imported_path,
            project_relative_path=material.relative_import_path,
            config=self.config,
            source_family=material.source_family,
            source_family_subproduct=material.source_family_subproduct,
        )
        return self._annotate_parsed_document(
            parsed_document,
            detection=FamilyDetection(
                source_family=material.source_family,
                reason=material.detection_reason,
                subproduct=material.source_family_subproduct,
            ),
            archive_member=material.archive_member,
        )

    def _annotate_parsed_document(
        self,
        parsed_document: ParsedDocument,
        *,
        detection: FamilyDetection,
        archive_member: str | None,
    ) -> ParsedDocument:
        metadata = dict(parsed_document.source.metadata)
        metadata["source_family"] = detection.source_family.value
        metadata["source_family_reason"] = detection.reason
        if detection.subproduct:
            metadata["source_family_subproduct"] = detection.subproduct
        if archive_member:
            metadata["archive_member"] = archive_member
        return parsed_document.model_copy(
            update={
                "source": parsed_document.source.model_copy(
                    update={"metadata": metadata}
                )
            }
        )

    def _import_path_for(self, *, path: Path, root: Path) -> Path:
        return self.project_root / "raw" / "imported" / self._relative_import_path_for(path=path, root=root)

    def _relative_import_path_for(self, *, path: Path, root: Path) -> Path:
        root_name = slugify(root.name or "imported")
        return Path(root_name) / path.relative_to(root)

    def _archive_relative_root(self, *, path: Path, root: Path) -> Path:
        archive_relative = path.relative_to(root)
        return Path(slugify(root.name or "imported")) / archive_relative.parent / archive_relative.stem

    def _is_archive(self, path: Path) -> bool:
        return path.suffix.lower() in ARCHIVE_SUFFIXES

    def _unsafe_archive_member(self, member_path: Path) -> bool:
        return member_path.is_absolute() or ".." in member_path.parts

    def _ingestable_archive_member(self, *, archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bool:
        member_path = Path(info.filename)
        if ingestable_file(member_path):
            return True
        with archive.open(info) as handle:
            return sniff_text_bytes(handle.read(4096))

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

    def _write_ingest_manifest(self, *, root: Path, entries: list[IngestManifestEntry]) -> Path:
        manifest_root = self.project_root / "state" / "manifests"
        manifest_root.mkdir(parents=True, exist_ok=True)
        manifest_id = f"ingest_{slugify(root.name or 'root')}_{short_hash(f'{root.resolve()}:{iso_now()}', length=10)}"
        manifest = IngestManifest(
            manifest_id=manifest_id,
            root_uri=root.resolve().as_uri(),
            generated_at=datetime.now(tz=UTC),
            materials=sorted(entries, key=lambda entry: entry.relative_import_path),
        )
        manifest_path = manifest_root / f"{manifest_id}.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
        return manifest_path

    def _append_log(self, line: str) -> None:
        log_path = self.project_root / "tree" / "log.md"
        with log_path.open("a", encoding="utf-8") as handle:
            if log_path.stat().st_size == 0:
                handle.write("# Ingest Log\n")
            handle.write(f"{line}\n")

    def _summarize_materials(self, materials: list[ImportMaterial]) -> DiscoverySummary:
        summary = DiscoverySummary(total_materials=len(materials))
        for material in materials:
            if material.archive_member:
                summary.archive_members += 1
            else:
                summary.direct_files += 1
            root_name = _material_root_name(material.relative_import_path)
            summary.by_root[root_name] = summary.by_root.get(root_name, 0) + 1
            family_name = material.source_family.value
            summary.by_family[family_name] = summary.by_family.get(family_name, 0) + 1
            if material.source_family_subproduct:
                subproduct_key = f"{family_name}:{material.source_family_subproduct}"
                summary.by_family_subproduct[subproduct_key] = (
                    summary.by_family_subproduct.get(subproduct_key, 0) + 1
                )
        return summary

    def _write_progress(
        self,
        *,
        status: str,
        root: Path,
        result: BatchResult,
        discovery: DiscoverySummary,
        total_materials: int,
        current_index: int | None = None,
        current_material: ImportMaterial | None = None,
    ) -> Path:
        progress_path = self.project_root / "state" / "progress.json"
        payload: dict[str, object] = {
            "status": status,
            "root_uri": root.resolve().as_uri(),
            "updated_at": iso_now(),
            "materials": {
                "discovered": discovery.total_materials,
                "direct_files": discovery.direct_files,
                "archive_members": discovery.archive_members,
                "by_root": discovery.by_root,
                "by_family": discovery.by_family,
                "by_family_subproduct": discovery.by_family_subproduct,
            },
            "counts": {
                "imported": result.imported,
                "processed": result.processed,
                "skipped": result.skipped,
                "failed": result.failed,
                "deleted": result.deleted,
            },
            "progress": {
                "completed": result.imported + result.failed,
                "total": total_materials,
                "current_index": current_index,
            },
        }
        if current_material:
            payload["current_material"] = {
                "relative_import_path": current_material.relative_import_path.as_posix(),
                "source_path": current_material.source_path.resolve().as_posix(),
                "source_family": current_material.source_family.value,
                "source_family_subproduct": current_material.source_family_subproduct,
                "archive_member": current_material.archive_member,
                "detection_reason": current_material.detection_reason,
            }
        progress_path.write_text(json.dumps(payload, indent=2) + "\n")
        return progress_path


def _chunk_document(document: ParsedDocument) -> list[ParsedDocument]:
    if not document.spans:
        return [document]

    chunks: list[ParsedDocument] = []
    current_spans: list[ParsedSpan] = []
    current_characters = 0

    for span in document.spans:
        span_length = len(span.text)
        would_overflow = (
            current_spans
            and (
                len(current_spans) >= MAX_EXTRACTION_SPANS
                or current_characters + span_length > MAX_EXTRACTION_CHARACTERS
            )
        )
        if would_overflow:
            chunks.append(ParsedDocument(source=document.source, text="", spans=current_spans))
            current_spans = []
            current_characters = 0

        current_spans.append(span)
        current_characters += span_length

    if current_spans:
        chunks.append(ParsedDocument(source=document.source, text="", spans=current_spans))

    return chunks


def _chunk_fingerprint(document: ParsedDocument) -> str:
    payload = [
        {
            "span_id": span.span_id,
            "span_start": span.span_start,
            "span_end": span.span_end,
            "text": span.text,
        }
        for span in document.spans
    ]
    return short_hash(json.dumps(payload, sort_keys=True), length=16)


def _normalize_evidence_items(source_id: str, evidence_items: list[EvidenceItem]) -> list[EvidenceItem]:
    normalized_by_id: dict[str, EvidenceItem] = {}
    for item in evidence_items:
        normalized = item.model_copy(
            update={
                "source_id": source_id,
                "quote": " ".join(item.quote.split()),
                "skill_candidates": sorted(set(item.skill_candidates)),
                "artifact_candidates": sorted(set(item.artifact_candidates)),
            }
        )
        evidence_id = _stable_evidence_id(normalized)
        normalized = normalized.model_copy(update={"evidence_id": evidence_id})
        existing = normalized_by_id.get(evidence_id)
        if existing is None or normalized.confidence > existing.confidence:
            normalized_by_id[evidence_id] = normalized

    return sorted(
        normalized_by_id.values(),
        key=lambda item: (item.span_start, item.span_end, item.evidence_type.value, item.evidence_id),
    )


def _stable_evidence_id(item: EvidenceItem) -> str:
    payload = {
        "source_id": item.source_id,
        "span_start": item.span_start,
        "span_end": item.span_end,
        "quote": item.quote,
        "evidence_type": item.evidence_type.value,
        "signal_class": item.signal_class.value,
        "skill_candidates": item.skill_candidates,
        "artifact_candidates": item.artifact_candidates,
    }
    return f"ev_{short_hash(json.dumps(payload, sort_keys=True), length=16)}"


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

def _material_root_name(relative_import_path: Path) -> str:
    parts = relative_import_path.parts
    if len(parts) >= 2:
        return parts[1]
    if parts:
        return parts[0]
    return "root"

def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ",".join(f"{name}:{counts[name]}" for name in sorted(counts))


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
