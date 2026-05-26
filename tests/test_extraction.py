from __future__ import annotations

from datetime import UTC, datetime

from traccia.extraction import extract_evidence
from traccia.models import (
    EvidenceType,
    ParsedDocument,
    ParsedSpan,
    ReliabilityTier,
    Sensitivity,
    SignalClass,
    SourceCategory,
    SourceDocument,
    SourceStatus,
    SourceType,
)


def test_implemented_evidence_from_authored_text_is_artifact_backed() -> None:
    document = _document(
        text="I built a Python data pipeline.",
        source_type=SourceType.MARKDOWN,
        source_category=SourceCategory.AUTHORED_CONTENT,
    )

    result = extract_evidence(document)

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.evidence_type == EvidenceType.IMPLEMENTED
    assert evidence.signal_class == SignalClass.ARTIFACT_BACKED_WORK
    assert evidence.reliability == ReliabilityTier.TIER_B
    assert evidence.confidence >= 0.8


def test_ai_dialogue_extraction_ignores_non_user_agent_log_spans() -> None:
    source = SourceDocument(
        source_id="src_agent_log",
        uri="file:///tmp/agent-log.md",
        source_type=SourceType.CHAT,
        source_category=SourceCategory.AI_DIALOGUE,
        parser="agent-log-markdown",
        sha256="deadbeef",
        created_at=datetime(2026, 4, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 1, tzinfo=UTC),
        title=None,
        language="en",
        sensitivity=Sensitivity.PRIVATE,
        metadata={
            "filename": "agent-log.md",
            "attribution_policy": "only user/human/developer spans may produce person-skill evidence",
        },
        status=SourceStatus.ACTIVE,
    )
    spans = [
        ParsedSpan(
            span_id="span_user",
            source_id=source.source_id,
            segment_kind="structured_entry",
            heading="user",
            text="User: I built a Python parser.",
            span_start=0,
            span_end=29,
            line_start=1,
            line_end=1,
        ),
        ParsedSpan(
            span_id="span_assistant",
            source_id=source.source_id,
            segment_kind="structured_entry",
            heading="assistant",
            text="Assistant: I debugged the storage layer.",
            span_start=31,
            span_end=70,
            line_start=3,
            line_end=3,
        ),
        ParsedSpan(
            span_id="span_thinking",
            source_id=source.source_id,
            segment_kind="structured_entry",
            heading="thinking",
            text="Thinking: I implemented TypeScript support.",
            span_start=72,
            span_end=113,
            line_start=5,
            line_end=5,
        ),
    ]
    document = ParsedDocument(source=source, text="\n\n".join(span.text for span in spans), spans=spans)

    result = extract_evidence(document)

    assert len(result.evidence_items) == 1
    assert result.evidence_items[0].quote == "User: I built a Python parser."
    assert result.evidence_items[0].skill_candidates == ["Python"]


def test_weak_social_profile_claim_stays_self_claimed() -> None:
    document = _document(
        text="Python enthusiast and machining hobbyist.",
        source_type=SourceType.TEXT,
        source_category=SourceCategory.SOCIAL_OR_COMMUNITY_TRACE,
        filename="profile.txt",
    )

    result = extract_evidence(document)

    assert result.evidence_items
    evidence = result.evidence_items[0]
    assert evidence.evidence_type == EvidenceType.SELF_CLAIMED
    assert evidence.signal_class == SignalClass.SELF_PRESENTATION
    assert evidence.reliability == ReliabilityTier.TIER_C
    assert evidence.confidence < 0.5


def test_code_without_named_skill_infers_python_implementation() -> None:
    document = _document(
        text="def build_graph():\n    return []",
        source_type=SourceType.CODE,
        source_category=SourceCategory.PRODUCED_ARTIFACT,
    )

    result = extract_evidence(document)

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.skill_candidates == ["Python"]
    assert evidence.evidence_type == EvidenceType.IMPLEMENTED
    assert evidence.reliability == ReliabilityTier.TIER_A


def _document(
    *,
    text: str,
    source_type: SourceType,
    source_category: SourceCategory,
    filename: str = "note.md",
) -> ParsedDocument:
    source = SourceDocument(
        source_id="src_test",
        uri="file:///tmp/note.md",
        source_type=source_type,
        source_category=source_category,
        parser="test",
        sha256="deadbeef",
        created_at=datetime(2026, 4, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 4, 1, tzinfo=UTC),
        title=None,
        language="en",
        sensitivity=Sensitivity.PRIVATE,
        metadata={"filename": filename},
        status=SourceStatus.ACTIVE,
    )
    span = ParsedSpan(
        span_id="span_1",
        source_id=source.source_id,
        segment_kind="paragraph",
        heading=None,
        text=text,
        span_start=0,
        span_end=len(text),
        line_start=1,
        line_end=1,
    )
    return ParsedDocument(source=source, text=text, spans=[span])
