# ATL-A.20 — Trusted Deployment Incident Remediation and Recovery Authorization

ATL-A.20 is the locked recovery door after a deployment integrity incident.

The recovery evidence chain is: incident → immutable remediation request → signed decision → execution attestation → independent integrity/outcome verification → resolution eligibility.

Recovery is fail-closed. An approval binds exactly one incident, deployment, artifact, tenant, environment and remediation action fingerprint. Changed, expired, rejected, or unverifiable approvals cannot authorize recovery. An execution never closes an incident; only passed post-remediation verification makes it eligible for ATL-A.21 resolution. The public projection exposes operational evidence only and never policy reasoning or internal scoring.
