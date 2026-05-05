from __future__ import annotations

from pathlib import Path

from traccia.utils import file_sha256, sentence_case_summary, short_hash, skill_id, slugify


def test_slugify_falls_back_for_empty_values() -> None:
    assert slugify("  !!!  ") == "item"


def test_skill_id_uses_stable_slug() -> None:
    assert skill_id("skill", "Metal & Machining") == "skill.metal-machining"


def test_short_hash_is_stable_and_length_limited() -> None:
    assert short_hash("same input", length=10) == short_hash("same input", length=10)
    assert len(short_hash("same input", length=10)) == 10


def test_file_sha256_reads_file_contents(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("traccia\n", encoding="utf-8")

    assert file_sha256(sample) == "29ce7a26e76ea6a4a4cc93ce9ee43a98f1c99a1b6291eee9b2c357d2efe9e7dc"


def test_sentence_case_summary_compacts_lines() -> None:
    assert sentence_case_summary(["  first line  ", "", "second line"]) == "first line second line"
