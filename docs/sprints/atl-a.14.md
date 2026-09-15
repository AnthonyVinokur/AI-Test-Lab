# ATL-A.14 — Trusted Deployment Authorization

ATL-A.14 combines, without recomputing, one verified ATL-A.12 policy-decision attestation and one verified ATL-A.13 approval attestation. Exact artifact, digest, tenant, environment, release, scope, condition, policy, version, freshness, and lifecycle checks produce a deterministic fail-closed authorization outcome.

Only an `authorized` outcome can produce the immutable signed authorization. Its independent safe verifier detects tampering, substitution, expiration, revocation, supersession, and invalid lifecycle history without importing proprietary decision, approval, or authorization-policy logic. ATL-A.14 authorizes an exact deployment proposition; it does not execute or enforce deployment.
