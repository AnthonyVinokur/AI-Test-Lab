# ATL-A.05.08 — Deterministic Admission Decision

Combines prerequisites, exact binding, context, authorization, freshness, and replay
checks in one frozen order. The first policy rejection becomes a stable internal result;
identical inputs always produce the same decision and reason code.
