from __future__ import annotations

from datetime import UTC, datetime

from traccia.models import (
    EvidenceItem,
    FreshnessState,
    NodeStatus,
    PersonSkillState,
    PersonSkillStatus,
    SkillKind,
    SkillNode,
)
from traccia.taxonomy import SKILL_BY_NAME
from traccia.utils import iso_now, skill_id, slugify

PASSIVE_EVIDENCE_TYPES = {"mentioned", "self_claimed", "studied", "researched"}
STRONG_SIGNAL_CLASSES = {"artifact_backed_work", "problem_solving_trace"}
COMMUNITY_ACTION_TYPES = {"taught", "presented", "reviewed"}


def support_score(evidence_item: EvidenceItem) -> float:
    weight = {
        "implemented": 0.9,
        "debugged": 0.85,
        "designed": 0.78,
        "presented": 0.72,
        "taught": 0.75,
        "reviewed": 0.68,
        "studied": 0.5,
        "used_tool": 0.55,
        "mentioned": 0.2,
        "self_claimed": 0.12,
    }.get(evidence_item.evidence_type.value, 0.3)
    signal_multiplier = {
        "artifact_backed_work": 1.0,
        "problem_solving_trace": 0.8,
        "community_participation": 0.45,
        "self_presentation": 0.2,
        "ambient_interest": 0.12,
    }.get(evidence_item.signal_class.value, 0.2)
    return weight * signal_multiplier * evidence_item.confidence


def evidence_counts_as_strong_action(evidence_item: EvidenceItem) -> bool:
    if evidence_item.evidence_type.value in PASSIVE_EVIDENCE_TYPES:
        return False
    if evidence_item.signal_class.value in STRONG_SIGNAL_CLASSES:
        return True
    return (
        evidence_item.signal_class.value == "community_participation"
        and evidence_item.evidence_type.value in COMMUNITY_ACTION_TYPES
    )


def evidence_bucket_flags(evidence_items: list[EvidenceItem]) -> dict[str, bool]:
    return {
        "consumption_only": all(not evidence_counts_as_strong_action(item) for item in evidence_items),
        "weak_signal_only": all(
            item.signal_class.value in {"ambient_interest", "self_presentation", "community_participation"}
            for item in evidence_items
        ),
    }


def should_create_node(candidate_name: str, support_bucket: dict[str, object]) -> bool:
    if support_bucket.get("weak_signal_only"):
        return False
    if candidate_name in SKILL_BY_NAME and support_bucket["score"] >= 0.5 and not support_bucket["consumption_only"]:
        return True
    if candidate_name in SKILL_BY_NAME and support_bucket["score"] >= 0.25:
        return True
    if candidate_name in SKILL_BY_NAME and support_bucket["score"] >= 1.1:
        return True
    return bool(support_bucket["score"] >= 1.2)


def should_request_review(support_bucket: dict[str, object]) -> bool:
    evidence_items: list[EvidenceItem] = list(support_bucket["evidence"])
    if any(item.evidence_type.value == "self_claimed" for item in evidence_items):
        return True
    if support_bucket.get("weak_signal_only") and support_bucket["score"] > 0:
        return True
    return bool(support_bucket["score"] >= 0.45)


def build_skill_node(name: str) -> SkillNode:
    definition = SKILL_BY_NAME.get(name)
    domain_name = definition.domain if definition else "Programming"
    aliases = list(definition.aliases) if definition else []
    description = definition.description if definition else f"{name} skill."
    return SkillNode(
        skill_id=skill_id("skill", name),
        kind=SkillKind.SKILL,
        name=name,
        slug=slugify(name),
        aliases=aliases,
        description=f"{domain_name}::{description}",
        taxonomy_refs=[],
        status=NodeStatus.ACTIVE,
        created_by="system",
        last_updated=iso_now(),
    )


def build_skill_state(
    *,
    skill: SkillNode,
    evidence_items: list[EvidenceItem],
    locked: bool,
    hidden: bool,
) -> PersonSkillState:
    action_score = sum(
        support_score(item)
        for item in evidence_items
        if evidence_counts_as_strong_action(item)
    )
    total_score = sum(support_score(item) for item in evidence_items)
    consumption_only = all(not evidence_counts_as_strong_action(item) for item in evidence_items)

    if consumption_only:
        level = 2 if total_score >= 0.75 else 1
    elif action_score >= 1.6:
        level = 4
    elif action_score >= 0.8:
        level = 3
    else:
        level = 2

    confidence = min(
        0.99,
        (sum(item.confidence for item in evidence_items) / len(evidence_items)) + min(0.2, len(evidence_items) * 0.03),
    )
    return PersonSkillState(
        skill_id=skill.skill_id,
        level=level,
        xp=round(total_score * 100, 2),
        confidence=round(confidence, 2),
        recency_score=0.9,
        breadth_score=min(1.0, len({item.source_id for item in evidence_items}) / 3),
        depth_score=min(1.0, action_score / 2),
        artifact_score=min(1.0, sum(1 for item in evidence_items if item.evidence_type.value in {"implemented", "debugged"}) / 3),
        teaching_score=min(1.0, sum(1 for item in evidence_items if item.evidence_type.value in {"taught", "presented"}) / 2),
        first_seen_at=None,
        first_learned_at=None,
        last_evidence_at=latest_evidence_at(evidence_items),
        acquired_at=None,
        acquisition_basis=None,
        freshness=FreshnessState.ACTIVE,
        status=PersonSkillStatus.HIDDEN if hidden else PersonSkillStatus.ACTIVE,
        locked=locked,
        manual_note=None,
    )


def latest_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    values = [item.time_reference for item in evidence_items if item.time_reference]
    if not values:
        return None
    latest = max(values)
    normalized = latest.replace("Z", "+00:00") if latest.endswith("Z") else latest
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
