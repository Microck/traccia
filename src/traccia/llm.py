from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib import error, request

from pydantic import BaseModel, Field

from traccia.config import TracciaConfig
from traccia.extraction import extract_evidence as fake_extract_evidence
from traccia.models import EvidenceItem, ParsedDocument, SkillNode
from traccia.pipeline_support import (
    build_skill_node,
    build_skill_state,
    evidence_bucket_flags,
    should_create_node,
    should_request_review,
    support_score,
)
from traccia.taxonomy import DOMAIN_BY_NAME


class BackendError(RuntimeError):
    pass


class ExtractedEvidencePayload(BaseModel):
    evidence_items: list[EvidenceItem] = Field(default_factory=list)


class CanonicalSkillDecision(BaseModel):
    candidate_name: str
    action: str
    canonical_name: str | None = None
    skill_id: str | None = None
    reason: str
    aliases: list[str] = Field(default_factory=list)
    review_risk_level: str = "medium"


class ScorePayload(BaseModel):
    level: int
    confidence: float
    recency_score: float
    breadth_score: float
    depth_score: float
    artifact_score: float
    teaching_score: float
    freshness: str
    status: str
    manual_note: str | None = None
    rationale: str


@dataclass(slots=True)
class CanonicalizationRequest:
    candidate_name: str
    evidence_items: list[EvidenceItem]
    existing_skills: list[dict[str, object]]
    thresholds: dict[str, float | int]


@dataclass(slots=True)
class ScoringRequest:
    skill: SkillNode
    evidence_items: list[EvidenceItem]
    thresholds: dict[str, float | int]
    locked: bool
    hidden: bool


class LLMBackend(Protocol):
    def extract_evidence(self, *, prompt: str, document: ParsedDocument) -> list[EvidenceItem]:
        ...

    def canonicalize(
        self, *, prompt: str, request: CanonicalizationRequest,
    ) -> CanonicalSkillDecision:
        ...

    def score_skill(self, *, prompt: str, request: ScoringRequest) -> ScorePayload:
        ...

    def healthcheck(self) -> str:
        ...


class FakeLLMBackend:
    def extract_evidence(self, *, prompt: str, document: ParsedDocument) -> list[EvidenceItem]:
        del prompt
        return fake_extract_evidence(document).evidence_items

    def canonicalize(
        self, *, prompt: str, request: CanonicalizationRequest,
    ) -> CanonicalSkillDecision:
        del prompt
        support_bucket = {
            "evidence": request.evidence_items,
            "score": sum(support_score(item) for item in request.evidence_items),
        }
        support_bucket.update(evidence_bucket_flags(request.evidence_items))
        if request.candidate_name in DOMAIN_BY_NAME:
            return CanonicalSkillDecision(
                candidate_name=request.candidate_name,
                action="ignore",
                reason="Domain roots are handled separately.",
            )
        if should_create_node(request.candidate_name, support_bucket):
            skill = build_skill_node(request.candidate_name)
            return CanonicalSkillDecision(
                candidate_name=request.candidate_name,
                action=(
                    "use_existing"
                    if any(row["name"] == request.candidate_name for row in request.existing_skills)
                    else "create"
                ),
                canonical_name=skill.name,
                skill_id=skill.skill_id,
                reason="Strong enough support for canonical node creation.",
            )
        if should_request_review(support_bucket):
            return CanonicalSkillDecision(
                candidate_name=request.candidate_name,
                action="review",
                reason="Weak evidence for direct node creation.",
            )
        return CanonicalSkillDecision(
            candidate_name=request.candidate_name,
            action="ignore",
            reason="Insufficient evidence.",
        )

    def score_skill(self, *, prompt: str, request: ScoringRequest) -> ScorePayload:
        del prompt
        state = build_skill_state(
            skill=request.skill,
            evidence_items=request.evidence_items,
            locked=request.locked,
            hidden=request.hidden,
        )
        return ScorePayload(
            level=state.level,
            confidence=state.confidence,
            recency_score=state.recency_score,
            breadth_score=state.breadth_score,
            depth_score=state.depth_score,
            artifact_score=state.artifact_score,
            teaching_score=state.teaching_score,
            freshness=state.freshness.value,
            status=state.status.value,
            manual_note=state.manual_note,
            rationale=f"Derived from {len(request.evidence_items)} evidence item(s).",
        )

    def healthcheck(self) -> str:
        return "fake backend ready"


class OpenAICompatibleBackend:
    def __init__(self, config: TracciaConfig) -> None:
        api_key = os.getenv(config.backend.api_key_env)
        if not api_key:
            raise BackendError(
                "Missing required API key in env var "
                f"{config.backend.api_key_env} for provider {config.backend.provider}."
            )
        self.api_key = api_key
        self.config = config
        if config.backend.api_style != "chat_completions":
            raise BackendError(
                f"Unsupported api_style={config.backend.api_style}. Supported: chat_completions."
            )

    def extract_evidence(self, *, prompt: str, document: ParsedDocument) -> list[EvidenceItem]:
        payload = self._invoke_schema(
            schema_model=ExtractedEvidencePayload,
            schema_name="extract_evidence_payload",
            system_prompt=prompt,
            user_prompt=_document_payload(document),
        )
        return payload.evidence_items

    def canonicalize(
        self, *, prompt: str, request: CanonicalizationRequest,
    ) -> CanonicalSkillDecision:
        return self._invoke_schema(
            schema_model=CanonicalSkillDecision,
            schema_name="canonical_skill_decision",
            system_prompt=prompt,
            user_prompt=_canonicalization_payload(request),
        )

    def score_skill(self, *, prompt: str, request: ScoringRequest) -> ScorePayload:
        return self._invoke_schema(
            schema_model=ScorePayload,
            schema_name="score_skill_payload",
            system_prompt=prompt,
            user_prompt=_scoring_payload(request),
        )

    def _invoke_schema(
        self, *, schema_model, schema_name: str, system_prompt: str, user_prompt: str,
    ):
        response_format = self._response_format(schema_model=schema_model, schema_name=schema_name)
        body = {
            "model": self.config.backend.model,
            "messages": [
                {"role": "system", "content": self._system_prompt_for_schema(
                    system_prompt, schema_model,
                )},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": response_format,
        }
        response_body = self._post_json("/chat/completions", body)
        content = self._extract_message_content(response_body)
        return schema_model.model_validate_json(self._normalize_json_content(content))

    def _response_format(self, *, schema_model, schema_name: str) -> dict[str, object]:
        if self.config.backend.structured_output_mode == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_model.model_json_schema(),
                },
            }
        if self.config.backend.structured_output_mode == "json_object":
            return {"type": "json_object"}
        raise BackendError(
            "Unsupported structured_output_mode="
            f"{self.config.backend.structured_output_mode}. Supported: json_schema, json_object."
        )

    def _system_prompt_for_schema(self, system_prompt: str, schema_model) -> str:
        if self.config.backend.structured_output_mode != "json_object":
            return system_prompt
        schema_json = json.dumps(schema_model.model_json_schema(), sort_keys=True)
        return (
            f"{system_prompt}\n\n"
            "Return one JSON object only. "
            f"It must validate against this JSON Schema: {schema_json}"
        )

    def healthcheck(self) -> str:
        response_body = self._get_json("/models")
        model_count = len(response_body.get("data", [])) if isinstance(response_body, dict) else 0
        return f"backend reachable, models={model_count}"

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        url = f"{self.config.backend.base_url.rstrip('/')}{path}"
        retries = max(1, self.config.backend.max_retries)
        last_error: Exception | None = None
        for attempt_index in range(retries):
            try:
                req = request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=self._headers(),
                    method="POST",
                )
                with request.urlopen(req, timeout=self.config.backend.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error = BackendError(f"LLM backend request failed ({exc.code}): {body}")
                if exc.code not in {408, 409, 429, 500, 502, 503, 504} \
                        or attempt_index == retries - 1:
                    raise last_error from exc
            except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = BackendError(f"LLM backend request failed: {exc}")
                if attempt_index == retries - 1:
                    raise last_error from exc
            time.sleep(0.5 * (2**attempt_index))
        raise BackendError(f"LLM backend request failed: {last_error}")

    def _get_json(self, path: str) -> dict[str, object]:
        url = f"{self.config.backend.base_url.rstrip('/')}{path}"
        req = request.Request(url, headers=self._headers(), method="GET")
        try:
            with request.urlopen(req, timeout=self.config.backend.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BackendError(f"LLM backend healthcheck failed ({exc.code}): {body}") from exc
        except (error.URLError, json.JSONDecodeError) as exc:
            raise BackendError(f"LLM backend healthcheck failed: {exc}") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _extract_message_content(self, response_body: dict[str, object]) -> str | dict[str, object]:
        try:
            content = response_body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError(f"Malformed chat completion response: {response_body}") from exc
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                elif item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
            if text_parts:
                return "\n".join(text_parts)
        return content

    def _normalize_json_content(self, content: str | dict[str, object]) -> str:
        if isinstance(content, dict):
            return json.dumps(content)
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
        return stripped


def backend_from_config(config: TracciaConfig) -> LLMBackend:
    if config.backend.provider == "fake":
        return FakeLLMBackend()
    if config.backend.provider == "openai_compatible":
        return OpenAICompatibleBackend(config)
    raise BackendError(f"Unsupported backend provider: {config.backend.provider}")


def backend_summary(config: TracciaConfig) -> str:
    return (
        f"provider={config.backend.provider} "
        f"base_url={config.backend.base_url} "
        f"api_style={config.backend.api_style} "
        f"structured_output_mode={config.backend.structured_output_mode} "
        f"model={config.backend.model}"
    )


def load_prompt(project_root: Path, prompt_name: str) -> str:
    return (project_root / "config" / "prompts" / prompt_name).read_text()


def _document_payload(document: ParsedDocument) -> str:
    lines = [
        f"source_id: {document.source.source_id}",
        f"source_type: {document.source.source_type.value}",
        f"source_category: {document.source.source_category.value}",
        f"title: {document.source.title or ''}",
        "segments:",
    ]
    for span in document.spans:
        lines.append(
            f"- span_id={span.span_id} "
            f"line_start={span.line_start} "
            f"line_end={span.line_end} "
            f"text={span.text}"
        )
    return "\n".join(lines)


def _canonicalization_payload(request: CanonicalizationRequest) -> str:
    lines = [f"candidate_name: {request.candidate_name}", "evidence:"]
    for item in request.evidence_items:
        lines.append(
            f"- evidence_id={item.evidence_id} type={item.evidence_type.value} "
            f"signal_class={item.signal_class.value} "
            f"confidence={item.confidence} "
            f"quote={item.quote}"
        )
    lines.append("existing_skills:")
    for row in request.existing_skills:
        lines.append(f"- skill_id={row['skill_id']} name={row['name']} slug={row['slug']}")
    return "\n".join(lines)


def _scoring_payload(request: ScoringRequest) -> str:
    lines = [
        f"skill_id: {request.skill.skill_id}",
        f"skill_name: {request.skill.name}",
        f"threshold_consumption_max_level: {request.thresholds['consumption_max_level']}",
        "evidence:",
    ]
    for item in request.evidence_items:
        lines.append(
            f"- evidence_id={item.evidence_id} type={item.evidence_type.value} "
            f"signal_class={item.signal_class.value} "
            f"confidence={item.confidence} "
            f"quote={item.quote}"
        )
    return "\n".join(lines)
