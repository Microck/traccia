from pathlib import Path

from traccia.config import load_config
from traccia.models import EvidenceItem, PersonSkillState, SkillNode, SourceDocument


def test_config_schema_validates_default_fixture() -> None:
    config = load_config(Path("tests/fixtures/golden/project/config.yaml"))

    assert config.project_name == "fixture-traccia"
    assert config.pipeline.extractor_version == "phase-0"


def test_domain_models_validate_golden_samples() -> None:
    source_document = SourceDocument.model_validate_json(
        Path("tests/fixtures/golden/source-document.json").read_text()
    )
    evidence_item = EvidenceItem.model_validate_json(
        Path("tests/fixtures/golden/evidence-item.json").read_text()
    )
    skill_node = SkillNode.model_validate_json(
        Path("tests/fixtures/golden/skill-node.json").read_text()
    )
    skill_state = PersonSkillState.model_validate_json(
        Path("tests/fixtures/golden/person-skill-state.json").read_text()
    )

    assert source_document.source_id == "src_repo_readme"
    assert evidence_item.source_id == source_document.source_id
    assert skill_node.skill_id == skill_state.skill_id
    assert skill_state.level == 3
    assert skill_state.core_self_centrality > 0
