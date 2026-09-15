# ATL-A.15 — Trusted Deployment Admission Enforcement

ATL-A.15 converts ATL-A.14's independently verifiable authorization into a mandatory,
provider-neutral deployment gate. It strictly translates and canonicalizes the actual
attempt, verifies the authorization through ATL-A.14's safe verifier, requires exact
binding and current validity, atomically applies replay policy, and issues an immutable
receipt. Only `permitted` reaches the executor port. Every other state fails closed.

The sprint does not recompute evaluation, policy, approval, or authorization decisions and
does not add Kubernetes, cloud, CI/CD, or other production deployment integrations.
