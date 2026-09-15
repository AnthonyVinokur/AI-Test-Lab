# ATL-A.10.04 — Canonical Event Serialization and Digest

Adds deterministic RFC-8259 JSON bytes and SHA-256 event identities. Translation accepts exactly one
versioned schema and canonical UTC timestamps; unknown fields, algorithms, versions, non-canonical
bytes, and digest mismatches fail closed.
