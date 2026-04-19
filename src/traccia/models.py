from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TracciaModel(BaseModel):
    """Strict base model so fixture validation fails loudly on schema drift."""

    model_config = ConfigDict(extra="forbid")


class SourceType(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    CODE = "code"
    JSON = "json"
    CSV = "csv"
    CALENDAR = "calendar"
    CHAT = "chat"
    BOOKMARKS = "bookmarks"
    ISSUE_TRACKER = "issue_tracker"
    PORTFOLIO = "portfolio"
    SLIDES = "slides"
    IMAGE = "image"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    SENSITIVE = "sensitive"


class SourceStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"
    ERROR = "error"


class SourceCategory(StrEnum):
    AUTHORED_CONTENT = "authored_content"
    CONSUMED_CONTENT = "consumed_content"
    PLATFORM_EXPORT_ACTIVITY = "platform_export_activity"
    SOCIAL_OR_COMMUNITY_TRACE = "social_or_community_trace"
    AI_DIALOGUE = "ai_dialogue"
    EXECUTION_TRACE = "execution_trace"
    COLLABORATION_TRACE = "collaboration_trace"
    PRODUCED_ARTIFACT = "produced_artifact"
    METADATA_ONLY_ACTIVITY = "metadata_only_activity"


class ReliabilityTier(StrEnum):
    TIER_A = "tier_a"
    TIER_B = "tier_b"
    TIER_C = "tier_c"
    TIER_D = "tier_d"


class EvidenceType(StrEnum):
    MENTIONED = "mentioned"
    STUDIED = "studied"
    IMPLEMENTED = "implemented"
    DEBUGGED = "debugged"
    REVIEWED = "reviewed"
    DESIGNED = "designed"
    PRESENTED = "presented"
    TAUGHT = "taught"
    MANAGED = "managed"
    RESEARCHED = "researched"
    PLANNED = "planned"
    USED_TOOL = "used_tool"
    PRODUCED_ARTIFACT = "produced_artifact"
    RECEIVED_FEEDBACK = "received_feedback"
    PASSED_ASSESSMENT = "passed_assessment"
    SELF_CLAIMED = "self_claimed"


class SkillKind(StrEnum):
    DOMAIN = "domain"
    SKILL = "skill"
    SUBSKILL = "subskill"
    TOOL = "tool"
    METHOD = "method"
    TOPIC = "topic"
    ARTIFACT = "artifact"


class NodeStatus(StrEnum):
    ACTIVE = "active"
    HIDDEN = "hidden"
    REVIEW = "review"
    DISPUTED = "disputed"


class EdgeType(StrEnum):
    PARENT_OF = "parent_of"
    PART_OF = "part_of"
    PREREQUISITE_OF = "prerequisite_of"
    RELATED_TO = "related_to"
    USES_TOOL = "uses_tool"
    PRODUCES_ARTIFACT = "produces_artifact"
    SPECIALIZES = "specializes"
    DEMONSTRATED_BY = "demonstrated_by"


class FreshnessState(StrEnum):
    ACTIVE = "active"
    WARMING = "warming"
    STALE = "stale"
    HISTORICAL = "historical"


class PersonSkillStatus(StrEnum):
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    HIDDEN = "hidden"
    MANUAL = "manual"


class ClaimOrigin(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    MANUAL = "manual"


class SignalClass(StrEnum):
    AMBIENT_INTEREST = "ambient_interest"
    SELF_PRESENTATION = "self_presentation"
    COMMUNITY_PARTICIPATION = "community_participation"
    PROBLEM_SOLVING_TRACE = "problem_solving_trace"
    ARTIFACT_BACKED_WORK = "artifact_backed_work"


class ReviewRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceDocument(TracciaModel):
    source_id: str
    uri: str
    source_type: SourceType
    source_category: SourceCategory
    parser: str
    sha256: str
    created_at: datetime | None = None
    ingested_at: datetime
    title: str | None = None
    language: str | None = None
    sensitivity: Sensitivity
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: SourceStatus


class EvidenceItem(TracciaModel):
    evidence_id: str
    source_id: str
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    quote: str
    evidence_type: EvidenceType
    signal_class: SignalClass
    skill_candidates: list[str] = Field(default_factory=list)
    artifact_candidates: list[str] = Field(default_factory=list)
    time_reference: str | None = None
    reliability: ReliabilityTier
    extractor_version: str
    confidence: float = Field(ge=0.0, le=1.0)


class SkillNode(TracciaModel):
    skill_id: str
    kind: SkillKind
    name: str
    slug: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    taxonomy_refs: list[str] = Field(default_factory=list)
    status: NodeStatus
    created_by: str
    last_updated: datetime


class SkillEdge(TracciaModel):
    edge_id: str
    from_skill_id: str
    to_skill_id: str
    edge_type: EdgeType
    weight: float = Field(ge=0.0, le=1.0)
    source: str
    confidence: float = Field(ge=0.0, le=1.0)


class PersonSkillState(TracciaModel):
    skill_id: str
    level: int = Field(ge=0, le=5)
    xp: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    core_self_centrality: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    breadth_score: float = Field(ge=0.0, le=1.0)
    depth_score: float = Field(ge=0.0, le=1.0)
    artifact_score: float = Field(ge=0.0, le=1.0)
    teaching_score: float = Field(ge=0.0, le=1.0)
    first_seen_at: datetime | None = None
    first_learned_at: datetime | None = None
    first_strong_evidence_at: datetime | None = None
    last_evidence_at: datetime | None = None
    last_strong_evidence_at: datetime | None = None
    historical_peak_level: int | None = Field(default=None, ge=0, le=5)
    historical_peak_at: datetime | None = None
    acquired_at: datetime | None = None
    acquisition_basis: str | None = None
    freshness: FreshnessState
    status: PersonSkillStatus
    locked: bool = False
    manual_note: str | None = None


class Claim(TracciaModel):
    claim_id: str
    claim_type: str
    subject: str
    predicate: str
    object: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    origin: ClaimOrigin


class ReviewItem(TracciaModel):
    item_id: str
    reason: str
    proposed_change: dict[str, Any]
    evidence_ids: list[str] = Field(default_factory=list)
    risk_level: ReviewRiskLevel


class ParsedSpan(TracciaModel):
    span_id: str
    source_id: str
    segment_kind: str
    heading: str | None = None
    text: str
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)


class ParsedDocument(TracciaModel):
    source: SourceDocument
    text: str
    spans: list[ParsedSpan] = Field(default_factory=list)
