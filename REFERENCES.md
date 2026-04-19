# REFERENCES.md

## Baseline references you already pointed to

### Framing / impetus
- Nick Spisak tweet:
  https://x.com/NickSpisak_/status/2041012360668750229
- Nick Spisak follow-up:
  https://x.com/NickSpisak_/status/2040448463540830705

### Core pattern
- Andrej Karpathy gist:
  https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

### Concrete implementation reference
- atomicmemory / llm-wiki-compiler:
  https://github.com/atomicmemory/llm-wiki-compiler

## Strongest architectural references after deeper GitHub research

These are the most relevant public repos for `traccia`, even though none is an exact match for an evidence-backed personal skill graph.

### Best conceptual seed
- atomicmemory / llm-wiki-compiler
  https://github.com/atomicmemory/llm-wiki-compiler
  - closest match for immutable raw input, incremental compilation, and Obsidian-friendly derived artifacts

### Best heavy-duty donor
- swarmclawai / swarmvault
  https://github.com/swarmclawai/swarmvault
  - strongest donor for provenance tagging, approvals, graph exports, and local-first knowledge compilation

### Best repo-structured agent workflow reference
- SamurAIGPT / llm-wiki-agent
  https://github.com/SamurAIGPT/llm-wiki-agent
  - strongest reference for schema-driven repo maintenance, append-only log patterns, and Obsidian-compatible outputs

### Best polished product/UI reference
- nashsu / llm_wiki
  https://github.com/nashsu/llm_wiki
  - strongest reference for ingest queue UX, review flow, and local graph browsing

### Best graph/report donors
- safishamsi / graphify
  https://github.com/safishamsi/graphify
  - strongest reference for graph packaging, cache/update behavior, and `EXTRACTED` / `INFERRED` / `AMBIGUOUS` edge semantics
- Lum1104 / Understand-Anything
  https://github.com/Lum1104/Understand-Anything
  - strongest reference for interactive graph browsing and explanation-oriented graph UI

## Useful boundary and caution references

### Personal knowledge graph / personal data ingestion systems
- hanig / engram
  https://github.com/hanig/engram
- MurtazaPlumber68 / GraphVault
  https://github.com/MurtazaPlumber68/GraphVault
- saxenauts / persona
  https://github.com/saxenauts/persona
  - useful as warnings about how quickly whole-person archive systems become much broader than a skill graph

### Skill extraction / taxonomy helpers
- KonstantinosPetrakis / esco-skill-extractor
  https://github.com/KonstantinosPetrakis/esco-skill-extractor

### Skill-tree UI references
- RoninATX / Human-Skill-Tree
  https://github.com/RoninATX/Human-Skill-Tree
- nshadov / personal-skill-tree
  https://github.com/nshadov/personal-skill-tree
  - useful for visual motif only, not as architectural bases

## Negative references for `traccia`

These repos are relevant mostly because they show the wrong default framing for this project.

### Resume / CV -> skill graph
- NickSaulnier / SkillGraph
  https://github.com/NickSaulnier/SkillGraph
- brianmarti1994 / AI-Skill-Graph
  https://github.com/brianmarti1994/AI-Skill-Graph
- Rishet11 / SkillGraph
  https://github.com/Rishet11/SkillGraph
- LohitDamarla / SkillGraph-AI
  https://github.com/LohitDamarla/SkillGraph-AI
  - mostly job-fit, resume, onboarding, or gap-analysis systems rather than reflective self-archiving

## Why they matter

- Karpathy gist plus llm-wiki-compiler are the closest match for the raw -> compiled knowledge pattern.
- swarmvault is the richest donor for provenance, reviewability, and graph/report ideas.
- llm-wiki-agent and nashsu/llm_wiki are the best references for repo ergonomics and user-facing browsing.
- graphify and Understand-Anything are the strongest references for graph outputs and graph viewer interaction.
- resume-driven skill-graph repos are mostly anti-references because they bias the product toward hiring and gap analysis instead of reflective archival.

## Current conclusion

The best path is to build `traccia` from scratch while borrowing patterns, not to fork an existing project.

Recommended stance:
- borrow architecture heavily from `atomicmemory/llm-wiki-compiler`
- borrow provenance and review patterns selectively from `swarmvault`
- borrow repo and export conventions from `llm-wiki-agent`
- borrow viewer ideas from `nashsu/llm_wiki`, `graphify`, and `Understand-Anything`
- do not build directly on the job-search-oriented skill-graph repos
