# Changelog

All notable user-facing changes to Traccia are tracked here.

## 0.1.2

- Require pypdf 6.21.1 or later and refresh the lockfile to address the PDF
  parser vulnerabilities reported by the release dependency audit.

- Pin the npm launcher to this project's matching GitHub wheel instead of the
  unrelated package occupying the bare `traccia` name on PyPI.
- Publish the GitHub wheel before npm, and disable the inapplicable PyPI job.

- Make admin graph nodes keyboard-operable and keep a newly reopened drawer
  visible when an earlier closing animation finishes.
- Index admin graph endpoints once instead of repeatedly scanning every node
  while drawing edges.
- Add deterministic browser coverage for exported public/admin viewers and
  downloaded curation decisions using synthetic local data.

- Add repository maintenance files for agents, conduct, pull requests, issues,
  and example environment variables.
- Clarify repository documentation and maintainer verification commands.

## 0.1.0

- Initial local-first Traccia CLI.
- Project scaffolding, ingest, scoring, review, graph rendering, Obsidian
  export, viewer export, admin curation, and public publish support.
- Thin npm launcher package for Node-first environments.
