# Security Policy

## Purpose

AI Test Lab is developed with security, reproducibility, and protection of sensitive information as explicit engineering requirements.

This repository must not contain API keys, access tokens, passwords, private keys, customer secrets, confidential datasets, or other credentials.

## Reporting a Security Issue

Do not disclose security vulnerabilities, exposed credentials, or sensitive information in a public GitHub issue.

If GitHub private vulnerability reporting is available for this repository, use that mechanism.

Otherwise, contact the repository owner privately through the GitHub profile before publishing technical details.

## Secret Handling

Secrets must be supplied through environment variables, approved secret-management systems, or local configuration excluded from source control.

Examples include:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

Local `.env` files must never be committed.

A `.env.example` file may document variable names, but it must never contain real credentials.

## Required Response to Credential Exposure

If a credential is accidentally exposed:

1. Revoke or rotate the credential immediately.
2. Remove it from the current repository state.
3. Search the repository for similar exposures.
4. Review Git history and artifacts for historical exposure.
5. Review provider usage logs for unauthorized activity.
6. Sanitize Git history when appropriate.
7. Verify that replacement credentials are stored outside source control.

Deleting a credential from the latest commit does not make the historical credential secret again.

## Repository Security Rules

The following must not be committed:

- `.env` files containing credentials;
- API keys or access tokens;
- password files;
- private cryptographic keys;
- cloud credentials;
- customer confidential information;
- proprietary implementation intended for a private repository.

Generated reports must also be reviewed before publication when they may contain prompts, responses, customer data, or other sensitive evidence.

## Dependency and Code Security

Security-sensitive changes should:

- remain small and reviewable;
- include appropriate automated tests;
- avoid logging secrets;
- fail safely where practical;
- maintain stable public contracts where possible.

## Scope

This policy applies to the public AI Test Lab repository.

Private or commercial AI Test Lab components may be subject to additional security controls.
