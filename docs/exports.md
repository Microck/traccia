# Exports And Publishing

Traccia renders several projections from the same canonical graph state. Exports
are generated files, not the source of truth.

## Local Graph Exports

| Command | Output | Use it for |
| --- | --- | --- |
| `traccia export graph` | `graph/graph.json` | Machine-readable graph payload. |
| `traccia export profile` | `profile/skill.md` | Profile summary derived from graph state. |
| `traccia export skill-md` | `tree/nodes/` | One markdown page per skill. |
| `traccia tree` | terminal output | Quick CLI inspection. |
| `traccia tree --format mermaid` | terminal Mermaid | Lightweight diagram embedding. |

## Obsidian Export

```bash
traccia export obsidian --project-root my-traccia
```

Output:

```text
exports/obsidian/
  Skills/
  Domains/
  Evidence/
  Sources/
  Profiles/
  Graph/
```

The Obsidian export copies graph data and writes linked markdown notes for
browsing outside the CLI.

## Debug Report

```bash
traccia export debug-report --project-root my-traccia
```

The debug report is for maintainers and operators. It includes counts and
diagnostics without making raw source files the public interface.

## Public Viewer

```bash
traccia export viewer --project-root my-traccia
```

Output:

```text
exports/viewer/
```

The read-only viewer is a static skill map generated from the current graph. It
includes pan and zoom, search, filters, minimap, legend, node details, deep
links, responsive mobile surfaces, and optional procedural UI sound.

Public search covers skill names, areas/domains, and descriptions. It does not
search raw provenance or aliases because the public graph contract strips alias
data.

Disable sound by default:

```bash
traccia export viewer --project-root my-traccia --no-sound
```

## Admin Curation Viewer

```bash
traccia export admin --project-root my-traccia
```

Output:

```text
exports/viewer-admin/
```

The admin viewer includes the full internal graph, including hidden, disputed,
review, and low-confidence nodes. It can write curation decisions such as:

- Hide or restore a node.
- Mute a node.
- Feature or pin a node.
- Collapse or expand domains.
- Add public label or note overrides.
- Approve selected low-confidence or disputed nodes for publication.

When served locally, the save action writes `curation.json`. From a static file
server, the browser downloads `curation.json`; place it where publish expects it.

## Publish A Redacted Public Bundle

```bash
traccia export publish --project-root my-traccia
```

Default output:

```text
exports/viewer-public/
```

Choose another directory name under `exports/`:

```bash
traccia export publish --project-root my-traccia --output-dir public-map
```

Publish reads graph state plus `exports/viewer/curation.json`, applies curation
and redaction rules, and writes a separate public graph contract.

The public bundle excludes:

- Hidden nodes and hidden edges.
- Raw source paths.
- Raw excerpts.
- Sensitive evidence IDs.
- Private or redacted provenance.
- Disputed or review nodes unless explicitly approved.
- Low-confidence nodes unless explicitly approved.

Public node IDs remain the same as internal IDs unless an ID leaks private
information. In that case, publish generates stable `pub_<hash>` aliases and
keeps the mapping in `alias-map.json` next to the public bundle. That file is
admin-only and must not be deployed publicly.
