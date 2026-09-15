# ATL-A.11.04 — Canonical Entry Serialization and Digest

Uses deterministic RFC-8259 JSON, sorted keys, canonical whole-second UTC, UTF-8, and SHA-256. The same
entry always has identical bytes and digest; changing any bound field changes its identity.
