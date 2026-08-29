# AI Test Lab Intellectual Property Boundary

## Purpose

AI Test Lab uses an explicit intellectual-property boundary so publicly useful interfaces can evolve without unintentionally exposing commercially sensitive implementation.

Every significant new component should be classified before publication as:

- PUBLIC
- INTERNAL
- PROPRIETARY

## PUBLIC

Public components may be committed to this repository.

Typical examples include:

- public CLI contracts;
- public schemas and DTOs;
- documented dataset formats;
- basic deterministic assertions;
- integration interfaces;
- examples;
- public report contracts;
- compatibility contracts;
- documentation intended for users.

Public components should expose what consumers need to integrate with AI Test Lab without unnecessarily exposing internal implementation.

## INTERNAL

Internal components support operation of the public framework but are not automatically considered public product contracts.

Examples may include:

- runtime plumbing;
- adapters;
- normalization logic;
- compatibility helpers;
- internal service composition;
- operational utilities.

Before an INTERNAL component is intentionally exposed, its API and information content must be reviewed.

Internal implementation should not become a public dependency merely because it exists in the repository.

## PROPRIETARY

Proprietary capabilities must not be committed to this public repository.

Examples may include:

- proprietary scoring algorithms;
- evidence intelligence;
- advanced regression intelligence;
- governance decision logic;
- compliance decision logic;
- security and adversarial intelligence;
- risk-ranking algorithms;
- enterprise policy engines;
- commercially valuable orchestration;
- optimization algorithms;
- confidential customer-specific logic.

These capabilities should live behind approved private repositories, services, or other controlled boundaries.

## Public Contract Rule

Public consumers should depend on stable, versioned contracts rather than proprietary implementation.

Preferred pattern:

    Public input contract
            |
            v
    Controlled boundary
            |
            v
    Private implementation
            |
            v
    Public output contract

Where practical, internal domain objects should be transformed into explicit public DTOs or schemas before publication.

## Information Exposure Review

IP exposure can occur through more than source code.

Before publication, review:

- application source;
- tests;
- fixtures;
- documentation;
- architecture diagrams;
- JSON schemas;
- generated reports;
- error messages;
- logs;
- website JavaScript;
- screenshots;
- CI artifacts;
- example datasets.

Public evidence should demonstrate capability without revealing unnecessary proprietary implementation details.

## Sprint Requirement

For significant new AI Test Lab capabilities, explicitly record:

    IP Classification:
    [ ] PUBLIC
    [ ] INTERNAL
    [ ] PROPRIETARY

And verify:

    [ ] No credentials are exposed.
    [ ] No proprietary implementation is exposed.
    [ ] Public DTO/schema boundaries are respected.
    [ ] Logs and reports do not reveal protected internals.
    [ ] Website code does not duplicate protected core logic.

## External Contributions

External contributions require review for intellectual-property provenance, licensing implications, and confidential information.

Acceptance of a pull request does not remove the need to verify that contributed material may legally be incorporated into the project.

A formal contributor-license or developer-certificate policy may be adopted before substantial third-party contributions are accepted.

## Legal Notice

This document defines an engineering and repository-management policy. It is not a substitute for legal advice or a software license.

Licensing, trademark registration, copyright registration, patents, employment inventions, contractor assignments, and commercial agreements should be reviewed with qualified legal counsel when appropriate.
