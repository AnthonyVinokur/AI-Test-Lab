# IP.02 — Prevent Future Leakage

## Status

Complete

## Purpose

IP.02 converts the intellectual-property and secret-handling policy established in IP.01 into an automated repository enforcement boundary.

IP.01 defined what must not enter the public AI Test Lab repository.

IP.02 makes violations detectable by automation before they are merged.

## IP Classification

* [x] PUBLIC
* [ ] INTERNAL
* [ ] PROPRIETARY

The repository-boundary scanner and its CI integration are intentionally public infrastructure. They reveal repository safety rules, not proprietary AI Test Lab evaluation logic.

## Goals

* Prevent obvious credentials and secrets from being committed.
* Prevent prohibited private/proprietary directories from being tracked.
* Prevent sensitive cryptographic file types from entering the public repository.
* Detect recognizable provider-token patterns.
* Detect populated provider API-key assignments.
* Preserve safe documentation such as `.env.example`.
* Enforce the boundary automatically in CI.
* Require an explicit IP/security review on future pull requests.

## Implementation

### Repository Boundary Scanner

Added:

`src: scripts/check_repository_boundary.py`

The scanner operates against Git-tracked files using:

`git ls-files`

This is intentional.

The public repository boundary is defined by files that Git can publish, rather than ignored local files such as `.venv` or a developer's local `.env`.

The scanner checks tracked paths for:

* forbidden private directories;
* forbidden sensitive filenames;
* private-key and certificate file extensions;
* private-key content markers;
* recognizable OpenAI API-key patterns;
* recognizable Anthropic API-key patterns;
* recognizable Google API-key patterns;
* recognizable GitHub token patterns;
* populated provider API-key assignments.

### Protected Directories

The automated boundary rejects tracked content under directories including:

* `secrets/`
* `credentials/`
* `private/`
* `proprietary/`
* `enterprise-private/`
* `internal-private/`

These names correspond to the repository IP boundary established in IP.01.

### Safe Placeholder Handling

`.env.example` remains explicitly permitted.

Empty provider variables such as:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
```

do not trigger the scanner.

A regression discovered during development showed that the initial whitespace expression could cross newline boundaries and incorrectly interpret the next environment-variable name as a value.

The expression was hardened to permit spaces and tabs without crossing lines.

### Directory Boundary Precedence

An allowed filename does not override a prohibited directory.

For example:

```text
.env.example
```

is valid at an approved public path, while:

```text
proprietary/.env.example
```

is rejected.

This prevents filename exceptions from bypassing the higher-level IP boundary.

## Automated Tests

Added:

`tests/test_repository_boundary.py`

The focused contract verifies:

1. empty `.env.example` placeholders are accepted;
2. a real `.env` filename is rejected;
3. proprietary directories are rejected;
4. private-key file extensions are rejected;
5. OpenAI-style key patterns are detected;
6. Anthropic-style key patterns are detected;
7. populated provider assignments are detected;
8. empty assignments cannot accidentally consume the following line;
9. private-key content markers are detected;
10. normal API-variable documentation remains safe;
11. allowed filenames cannot bypass private-directory restrictions.

Fake credential strings in the tests are constructed at runtime rather than storing realistic-looking complete credentials directly in the repository.

## CI Enforcement

Updated:

`.github/workflows/python-tests.yml`

The existing GitHub Actions test job now runs:

```text
python scripts/check_repository_boundary.py
```

before the regular pytest suite.

A repository-boundary violation therefore fails CI and can participate in the existing protected-branch / required-check workflow.

## Pull Request Review Boundary

Added:

`.github/pull_request_template.md`

Future pull requests must explicitly review:

* IP classification;
* credential exposure;
* proprietary implementation exposure;
* DTO/schema boundaries;
* logs, reports, fixtures, examples, and test-data exposure;
* public-facing duplication of protected core logic;
* repository-boundary scanner status.

Automation catches objective leakage patterns.

Human architectural review remains responsible for deciding whether implementation is commercially valuable, proprietary, confidential, or otherwise unsuitable for publication.

## Verification

Repository boundary:

```text
Repository boundary check: PASS
```

Focused IP.02 tests:

```text
11 passed
```

Full regression suite:

```text
656 passed in 17.16s
```

Git whitespace validation:

```text
git diff --cached --check
```

Result:

```text
clean
```

## Security Boundary

IP.02 protects against future repository-state leakage.

It does not claim to remove material from historical Git commits. Historical credential exposure, credential rotation, history rewriting, provider audit logs, and incident-response procedures remain separate concerns.

No proprietary AI Test Lab scoring, governance, evidence-intelligence, compliance, security-intelligence, orchestration, or optimization algorithms were introduced by this sprint.

## Outcome

Before IP.02:

```text
Policy -> Developer remembers -> Review may catch mistake
```

After IP.02:

```text
IP policy
    |
    v
Git-tracked repository
    |
    v
Automated boundary scanner
    |
    v
CI enforcement
    |
    v
Pull-request IP/security review
    |
    v
Public repository
```

IP.02 therefore changes the IP boundary from a documentation-only rule into an enforceable engineering contract.
