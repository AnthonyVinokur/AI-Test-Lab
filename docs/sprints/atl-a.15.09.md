# ATL-A.15.09 — Provider-Neutral Enforcement Gateway

Adds the mandatory gateway and executor port. The executor is invoked exactly once for a
new permitted admission and never for blocked, invalid, indeterminate, verifier-failed, or
state-store-failed outcomes. No provider SDK or production adapter is introduced.
