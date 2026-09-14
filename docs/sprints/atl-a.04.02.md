# ATL-A.04.02 — Untrusted Trust-Policy Translation

Implemented strict translation from JSON-shaped mappings. The boundary rejects missing/extra fields, malformed base64/timestamps/statuses, duplicate scopes, duplicate signers, and duplicate keys. Values are copied into tuples, frozensets, bytes, and frozen records so later input mutation cannot change policy behavior.
