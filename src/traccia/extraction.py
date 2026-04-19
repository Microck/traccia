from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from traccia.models import (
    EvidenceItem,
    EvidenceType,
    ParsedDocument,
    ReliabilityTier,
    SignalClass,
    SourceCategory,
    SourceType,
)
from traccia.taxonomy import SKILL_BY_NAME, match_skill_names
from traccia.utils import short_hash


ACTION_PATTERNS: list[tuple[EvidenceType, tuple[str, ...]]] = [
    (EvidenceType.DEBUGGED, ("debugged", "fixed", "resolved", "troubleshot")),
    (EvidenceType.TAUGHT, ("taught", "mentored", "coached")),
    (EvidenceType.PRESENTED, ("presented", "demoed", "explained")),
    (EvidenceType.DESIGNED, ("designed", "architected", "planned")),
    (EvidenceType.IMPLEMENTED, ("built", "implemented", "wrote", "created", "developed", "stores results")),
    (EvidenceType.REVIEWED, ("reviewed", "review")),
    (EvidenceType.STUDIED, ("studied", "read", "learned", "researched")),
    (EvidenceType.USED_TOOL, ("using", "used", "with")),
]

EVIDENCE_BASE_CONFIDENCE = {
    EvidenceType.IMPLEMENTED: 0.88,
    EvidenceType.DEBUGGED: 0.85,
    EvidenceType.DESIGNED: 0.8,
    EvidenceType.PRESENTED: 0.74,
    EvidenceType.TAUGHT: 0.78,
    EvidenceType.REVIEWED: 0.72,
    EvidenceType.STUDIED: 0.64,
    EvidenceType.USED_TOOL: 0.68,
    EvidenceType.MENTIONED: 0.32,
    EvidenceType.SELF_CLAIMED: 0.25,
}


@dataclass(slots=True)
class ExtractionResult:
    evidence_items: list[EvidenceItem]
    unresolved_candidates: dict[str, list[str]]


def extract_evidence(document: ParsedDocument) -> ExtractionResult:
    evidence_items: list[EvidenceItem] = []
    unresolved_candidates: dict[str, list[str]] = defaultdict(list)

    for span in document.spans:
        candidate_names = match_skill_names(span.text)
        if not candidate_names and document.source.source_type != SourceType.CODE:
            continue

        evidence_type = _classify_evidence_type(document=document, text=span.text)
        if not candidate_names:
            candidate_names = _infer_from_source_type(document.source.source_type)
        if not candidate_names:
            continue

        confidence = _confidence_for(document=document, evidence_type=evidence_type)
        evidence_item = EvidenceItem(
            evidence_id=f"ev_{short_hash(f'{document.source.source_id}:{span.span_id}', length=12)}",
            source_id=document.source.source_id,
            span_start=span.span_start,
            span_end=span.span_end,
            quote=span.text.replace("\n", " ").strip(),
            evidence_type=evidence_type,
            signal_class=_signal_class_for(document=document, evidence_type=evidence_type, text=span.text),
            skill_candidates=candidate_names,
            artifact_candidates=_artifact_candidates(document.source.source_type),
            time_reference=_time_reference_for(document),
            reliability=_reliability_for(document=document, evidence_type=evidence_type),
            extractor_version="heuristic-v1",
            confidence=confidence,
        )
        evidence_items.append(evidence_item)

        if evidence_type in {EvidenceType.MENTIONED, EvidenceType.SELF_CLAIMED}:
            for name in candidate_names:
                unresolved_candidates[name].append(evidence_item.evidence_id)

    return ExtractionResult(evidence_items=evidence_items, unresolved_candidates=dict(unresolved_candidates))


def _time_reference_for(document: ParsedDocument) -> str | None:
    timestamp = document.source.created_at or document.source.ingested_at
    if not timestamp:
        return None
    return timestamp.isoformat()


def _classify_evidence_type(*, document: ParsedDocument, text: str) -> EvidenceType:
    lowered = text.lower()
    if (
        document.source.source_category == SourceCategory.SOCIAL_OR_COMMUNITY_TRACE
        and any(token in document.source.metadata.get("filename", "").lower() for token in ("profile", "bio", "about"))
    ):
        return EvidenceType.SELF_CLAIMED
    if "maybe learn" in lowered or "someday" in lowered:
        return EvidenceType.SELF_CLAIMED
    for evidence_type, patterns in ACTION_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return evidence_type
    if document.source.source_type == SourceType.CODE:
        return EvidenceType.IMPLEMENTED
    return EvidenceType.MENTIONED


def _confidence_for(*, document: ParsedDocument, evidence_type: EvidenceType) -> float:
    source_bonus = 0.07 if document.source.source_type == SourceType.CODE else 0.0
    signal_penalty = {
        SourceCategory.PRODUCED_ARTIFACT: 0.0,
        SourceCategory.AUTHORED_CONTENT: 0.0,
        SourceCategory.COLLABORATION_TRACE: 0.03,
        SourceCategory.AI_DIALOGUE: 0.08,
        SourceCategory.SOCIAL_OR_COMMUNITY_TRACE: 0.18,
        SourceCategory.PLATFORM_EXPORT_ACTIVITY: 0.22,
        SourceCategory.METADATA_ONLY_ACTIVITY: 0.22,
        SourceCategory.CONSUMED_CONTENT: 0.12,
        SourceCategory.EXECUTION_TRACE: 0.05,
    }.get(document.source.source_category, 0.0)
    return max(0.05, min(0.99, EVIDENCE_BASE_CONFIDENCE[evidence_type] + source_bonus - signal_penalty))


def _reliability_for(*, document: ParsedDocument, evidence_type: EvidenceType) -> ReliabilityTier:
    if document.source.source_type == SourceType.CODE:
        return ReliabilityTier.TIER_A
    if document.source.source_category in {SourceCategory.PLATFORM_EXPORT_ACTIVITY, SourceCategory.METADATA_ONLY_ACTIVITY}:
        return ReliabilityTier.TIER_D
    if document.source.source_category == SourceCategory.SOCIAL_OR_COMMUNITY_TRACE:
        return ReliabilityTier.TIER_C
    if document.source.source_category == SourceCategory.AI_DIALOGUE:
        return ReliabilityTier.TIER_C
    if evidence_type in {EvidenceType.IMPLEMENTED, EvidenceType.DEBUGGED, EvidenceType.DESIGNED}:
        return ReliabilityTier.TIER_B
    if evidence_type in {EvidenceType.PRESENTED, EvidenceType.TAUGHT, EvidenceType.REVIEWED, EvidenceType.STUDIED}:
        return ReliabilityTier.TIER_B
    return ReliabilityTier.TIER_C


def _artifact_candidates(source_type: SourceType) -> list[str]:
    return {
        SourceType.CODE: ["source code"],
        SourceType.MARKDOWN: ["markdown document"],
        SourceType.CSV: ["spreadsheet export"],
        SourceType.JSON: ["json artifact"],
        SourceType.PDF: ["pdf document"],
        SourceType.DOCX: ["docx document"],
        SourceType.TEXT: ["text document"],
    }.get(source_type, [])


def _infer_from_source_type(source_type: SourceType) -> list[str]:
    return {
        SourceType.CODE: ["Python"],
        SourceType.CSV: ["Documentation"],
    }.get(source_type, [])


def _signal_class_for(*, document: ParsedDocument, evidence_type: EvidenceType, text: str) -> SignalClass:
    del text
    source_category = document.source.source_category
    filename = document.source.metadata.get("filename", "").lower()

    if source_category == SourceCategory.PRODUCED_ARTIFACT:
        return SignalClass.ARTIFACT_BACKED_WORK
    if source_category in {SourceCategory.AUTHORED_CONTENT, SourceCategory.COLLABORATION_TRACE}:
        if evidence_type in {
            EvidenceType.IMPLEMENTED,
            EvidenceType.DEBUGGED,
            EvidenceType.DESIGNED,
            EvidenceType.REVIEWED,
            EvidenceType.PRESENTED,
            EvidenceType.TAUGHT,
        }:
            return SignalClass.ARTIFACT_BACKED_WORK
        return SignalClass.PROBLEM_SOLVING_TRACE
    if source_category == SourceCategory.AI_DIALOGUE:
        if evidence_type in {EvidenceType.IMPLEMENTED, EvidenceType.DEBUGGED, EvidenceType.DESIGNED, EvidenceType.REVIEWED}:
            return SignalClass.PROBLEM_SOLVING_TRACE
        return SignalClass.AMBIENT_INTEREST
    if source_category == SourceCategory.SOCIAL_OR_COMMUNITY_TRACE:
        if any(token in filename for token in ("profile", "bio", "about")):
            return SignalClass.SELF_PRESENTATION
        return SignalClass.COMMUNITY_PARTICIPATION
    if source_category in {SourceCategory.PLATFORM_EXPORT_ACTIVITY, SourceCategory.METADATA_ONLY_ACTIVITY, SourceCategory.CONSUMED_CONTENT}:
        return SignalClass.AMBIENT_INTEREST
    return SignalClass.AMBIENT_INTEREST
