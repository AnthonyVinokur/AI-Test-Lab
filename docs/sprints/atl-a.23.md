# ATL-A.23 — Trusted Deployment Readiness Revalidation

## Purpose

Before a consumer relies on a previous readiness attestation, evaluate the supplied current evidence again. Prior applicability and current readiness are separate results: expiry or evidence changes invalidate reliance on the old record, but complete current evidence may still establish fresh readiness. Revalidation never executes, promotes, rolls back, or authorizes deployment.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.23.01 | Frozen internal `ReadinessEvidenceBinding` associates the exact attestation, complete evidence snapshot, deployment identifier, evidence revision, and expiry. Existing immutable evidence identities are retained. |
| ATL-A.23.02 | Positive `timedelta` validity and explicit timezone-aware evaluation time; UTC normalization and whole-second precision follow existing contracts. |
| ATL-A.23.03 | Internal applicability reasons identify missing/mismatched bindings, changed evidence, invalid attestations/timestamps, future issuance, and expiry. Cross-deployment use raises normalized `DeploymentReadinessError`. |
| ATL-A.23.04 | Every accepted request invokes ATL-A.22 with current evidence and evaluation time, including recovery authorization checks. |
| ATL-A.23.05 | ATL-A.22 remains the single state-composition source. Known blocking reasons survive missing or future-dated evidence; unavailable evidence requires review. No old-ready fallback exists. |
| ATL-A.23.06 | Explicit projection returns the existing `PublicDeploymentReadinessAttestationV1` with its existing reason codes. |
| ATL-A.23.07 | Existing ATL-A.22 signatures, schema, reason codes, and behavior remain compatible. Revalidation metadata stays internal. |
| ATL-A.23.08 | Tests cover expiry boundaries, evidence changes, incident/integrity blocking, authorization expiry, missing evidence, determinism, public allowlisting, and compatibility. |

ATL-A.22 receives one corrective change: its recovery authorization helper raises `RecoveryError` for expired or rejected authorization. Readiness now converts that exception to its existing `recovery_authorization_invalid` blocking reason, consistent with the defined readiness behavior. Successful calls and the public schema remain unchanged.

## Internal usage

Use `attest_bound_deployment_readiness(evidence=..., evaluation_time=..., validity=...)` to evaluate and bind together. Persist the returned binding alongside the historical record. Do not retroactively attach current evidence to an old attestation.

Call `revalidate_deployment_readiness(previous=..., binding=..., evidence=..., evaluation_time=..., validity=...)` before reliance. The result includes a fresh attestation, its new binding, and internal `previous_applicability_reasons`. Use `public_deployment_readiness_revalidation(result)` for public output. Only `ready` is eligible wherever readiness is required; `blocked` and `review_required` are both ineligible.

`ReadinessEvidence` requires an explicit deployment identifier, store revision, integrity result (or `None`), and incident record (or `None`). Explicit `incident=None` with `incident_evidence_available=True` means the caller has checked and confirmed no incident. If incident information is unavailable, set the flag to `False`; do not represent an unknown incident inventory as a confirmed absence. Missing integrity is represented by `None`. The caller must supply a consistent current snapshot and update the revision when the deployment or evidence changes. Full snapshot equality also detects changed supplied evidence even if a caller reuses a revision.

## Time and decision semantics

Previous freshness is exactly `issued_at <= evaluation_time < expires_at`. Equality at expiry is expired; future issuance cannot establish freshness. Each binding stores its original expiry, so a new validity duration applies only to the newly issued record. Nonpositive, fractional-second, overflowing validity durations and invalid evaluation times raise normalized errors before issuing a result.

An expired, unbound, damaged, or evidence-mismatched prior record is never reused. Fresh current evidence can establish readiness independently. A prior attestation or binding for another deployment is rejected outright. Historical records remain unchanged. Current event timestamps must not be later than evaluation time; authorization expiry timestamps may be in the future. Unusable current timestamps add the existing `integrity_evidence_unavailable` reason without suppressing known blocking reasons.

For example, a previously ready deployment with a new open incident becomes blocked, even when integrity evidence is missing. A resolved incident whose recovery authorization has expired follows ATL-A.22's authorization rules. Expiry of the old readiness record alone does not imply unsafe deployment.

## IP classification and limits

- PUBLIC: unchanged ATL-A.22 readiness DTO and normalized reason codes.
- INTERNAL: evidence snapshots, bindings, applicability reasons, and the bounded revalidation adapter.
- PROPRIETARY: no new policy engine, evidence intelligence, scoring, or commercial decision mechanics introduced or exposed.

Bindings provide association, not proof of authenticity. Neither a revision nor an existing digest authenticates its producer. The caller remains responsible for obtaining trusted, complete, current evidence and preserving its provenance. This sprint adds no background observation, evidence fetching, infrastructure, configurable policy engine, or independent cryptographic verification. Public output excludes evidence revisions, internal digests, binding expiry, applicability diagnostics, signatures, incident details, and recovery internals. No credentials or protected internals are logged or exported.

## Validation

Run `python -m pytest tests/test_reference_architecture_deployment_readiness*.py -q` for focused coverage, then `python -m pytest -m "not integration" -q` and the three repository boundary scripts used by CI.

Implementation validation (Python 3.12 workspace): **45 focused tests passed**;
**1,454 non-integration tests passed, 1 integration test deselected**. Repository,
public-export, and private-dependency boundary checks passed. CI remains responsible
for its configured Python 3.13 environment and pinned dependency set.
