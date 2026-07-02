# Security Policy

## Supported Versions

Traccia is pre-1.0. Security fixes target the current `main` branch and the
latest published release.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability.

Report security problems by using GitHub private vulnerability reporting when it
is available for this repository, or by emailing `contact@micr.dev`.

Please include:

- Affected version or commit.
- A short description of the issue.
- Reproduction steps or a proof of concept when safe to share.
- Any known impact on local archives, generated public exports, credentials, or
  packaged releases.

Expect an initial response within 7 days. Confirmed issues are handled with the
smallest fix that removes the risk, followed by a public note once users have a
safe upgrade path.

## Scope

Security reports are especially relevant for:

- Private source data leaking into public viewer exports.
- Credentials, API keys, or personal archive paths appearing in generated files.
- Unsafe archive or document parsing behavior.
- Package release, npm launcher, or workflow supply-chain issues.

General bugs, feature requests, and support questions should use the normal
issue templates instead.
