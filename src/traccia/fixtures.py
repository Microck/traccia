from __future__ import annotations

from pathlib import Path

from traccia.config import TracciaConfig, load_config
from traccia.models import EvidenceItem, PersonSkillState, SkillNode, SourceDocument, TracciaModel


class FixtureManifest(TracciaModel):
    config_path: str
    source_document_path: str
    evidence_item_path: str
    skill_node_path: str
    person_skill_state_path: str
    sample_source_text_path: str


class GoldenFixtureBundle(TracciaModel):
    config: TracciaConfig
    source_document: SourceDocument
    evidence_item: EvidenceItem
    skill_node: SkillNode
    person_skill_state: PersonSkillState
    sample_source_text: str


def load_golden_fixture_bundle(root: Path) -> GoldenFixtureBundle:
    manifest_path = root / "manifest.json"
    manifest = FixtureManifest.model_validate_json(manifest_path.read_text())

    return GoldenFixtureBundle(
        config=load_config(root / manifest.config_path),
        source_document=SourceDocument.model_validate_json(
            (root / manifest.source_document_path).read_text()
        ),
        evidence_item=EvidenceItem.model_validate_json(
            (root / manifest.evidence_item_path).read_text()
        ),
        skill_node=SkillNode.model_validate_json((root / manifest.skill_node_path).read_text()),
        person_skill_state=PersonSkillState.model_validate_json(
            (root / manifest.person_skill_state_path).read_text()
        ),
        sample_source_text=(root / manifest.sample_source_text_path).read_text(),
    )
