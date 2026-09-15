# ATL-A.06.02 — Untrusted Append Request Translation

Strict translation requires the exact public request schema, canonical contract identity,
valid identifiers, and lowercase SHA-256 digests. Caller-selected status, sequence,
recorded time, chain identity, entry identity, and unknown fields are rejected.
