# ATL-A.14.07 — Deterministic Authorization Decision

Evaluates trusted references, exact cross-binding, policy preconditions, and explicit request time in a fixed fail-closed order. Equivalent inputs return equivalent `authorized`, `denied`, `indeterminate`, or `invalid` outcomes with stable sanitized reason codes; only `authorized` permits issuance.
