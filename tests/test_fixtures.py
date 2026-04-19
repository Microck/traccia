from pathlib import Path

from traccia.fixtures import load_golden_fixture_bundle


def test_golden_fixture_bundle_loads() -> None:
    bundle = load_golden_fixture_bundle(Path("tests/fixtures/golden"))

    assert bundle.source_document.source_id == "src_repo_readme"
    assert bundle.evidence_item.evidence_id == "ev_repo_readme_python_cli"
    assert bundle.skill_node.slug == "python-cli-tooling"
    assert "CLI" in bundle.sample_source_text
