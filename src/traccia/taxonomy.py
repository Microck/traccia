from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DomainDefinition:
    """A named skill domain with a description."""
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """A skill entry with domain, aliases, and regex match patterns."""
    name: str
    domain: str
    description: str
    aliases: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    kind: str = "skill"


DOMAINS: tuple[DomainDefinition, ...] = (
    DomainDefinition("Programming", "Languages, tooling, and software implementation."),
    DomainDefinition("Data", "Data formats, storage, and analysis capabilities."),
    DomainDefinition("Documentation", "Written communication and durable documentation."),
    DomainDefinition("Collaboration", "Teaching, review, and cross-team communication."),
    DomainDefinition("Operations", "Delivery, debugging, and system operations."),
)

SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        name="Python",
        domain="Programming",
        description="Building automation and application logic in Python.",
        aliases=("py",),
        patterns=(r"\bpython\b", r"\.py\b"),
    ),
    SkillDefinition(
        name="Rust",
        domain="Programming",
        description="Systems programming and performance-oriented application development in Rust.",
        patterns=(r"\brust\b",),
    ),
    SkillDefinition(
        name="SQLite",
        domain="Data",
        description="Embedded relational data storage with SQLite.",
        patterns=(r"\bsqlite\b",),
    ),
    SkillDefinition(
        name="JSON",
        domain="Data",
        description="Structured data interchange and serialization with JSON.",
        patterns=(r"\bjson\b",),
    ),
    SkillDefinition(
        name="CSV",
        domain="Data",
        description="Tabular data handling with CSV exports and imports.",
        patterns=(r"\bcsv\b",),
    ),
    SkillDefinition(
        name="Markdown",
        domain="Documentation",
        description="Lightweight documentation authoring in Markdown.",
        patterns=(r"\bmarkdown\b", r"\bmd\b"),
    ),
    SkillDefinition(
        name="Documentation",
        domain="Documentation",
        description="Writing and maintaining technical documentation.",
        patterns=(r"\bdocs\b", r"\bwrite cli docs\b", r"\bdocumentation refresh\b"),
    ),
    SkillDefinition(
        name="CLI tooling",
        domain="Programming",
        description="Designing and building command-line tools.",
        aliases=("cli", "command-line"),
        patterns=(r"\bcli\b", r"\bcommand[- ]line\b"),
    ),
    SkillDefinition(
        name="Debugging",
        domain="Operations",
        description="Diagnosing and resolving defects and runtime issues.",
        patterns=(r"\bdebugg(?:ed|ing)?\b", r"\bparser edge cases\b"),
    ),
    SkillDefinition(
        name="Teaching",
        domain="Collaboration",
        description="Explaining or teaching technical material to others.",
        patterns=(r"\btaught\b", r"\bpresented\b", r"\blessons learned\b"),
    ),
    SkillDefinition(
        name="Ingestion pipelines",
        domain="Programming",
        description="Building deterministic pipelines for source intake and transformation.",
        patterns=(r"\bingestion pipeline\b", r"\bingests\b"),
    ),
    SkillDefinition(
        name="Redis",
        domain="Data",
        description="In-memory data structures and caching with Redis.",
        patterns=(r"\bredis\b",),
    ),
)

DOMAIN_BY_NAME = {domain.name: domain for domain in DOMAINS}
SKILL_BY_NAME = {skill.name: skill for skill in SKILLS}


@dataclass(slots=True)
class MatchResult:
    """Holds the set of skill names matched from a text scan."""
    names: set[str] = field(default_factory=set)


def match_skill_names(text: str) -> list[str]:
    """Return skill names whose patterns match *text*."""
    lowered = text.lower()
    matched: list[str] = []
    for skill in SKILLS:
        if any(re.search(pattern, lowered) for pattern in skill.patterns):
            matched.append(skill.name)
    return matched
