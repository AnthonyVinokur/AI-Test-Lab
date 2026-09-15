# ATL-A.22 — Trusted Deployment Readiness Attestation

ATL-A.22 converts existing trusted-deployment evidence into one deterministic, public readiness decision for a single deployment. It never promotes, rolls back, or changes a deployment; CI/CD and human approvers can consume its attestation as release evidence.

The attestation has three states: `ready`, `blocked`, and `review_required`. A deployment is ready only when integrity is trusted and there is no unresolved incident. A resolved incident additionally requires an exact, unexpired recovery authorization, successful remediation verification, and a valid immutable closure record.

The boundary fails closed. Known unsafe facts, such as untrusted integrity or an open incident, return `blocked`. Missing or indeterminate evidence returns `review_required`. Public output contains only the deployment identifier, state, normalized reason codes, and time. It intentionally excludes recovery signatures, incident evidence, root-cause data, preventive-action details, and internal decision mechanics.
