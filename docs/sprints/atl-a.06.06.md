# ATL-A.06.06 — Append-Only Chain Construction

A new evidence version explicitly supersedes the current chain head. Its immutable entry
records the preceding entry digest and ID; earlier entries remain unchanged. No blockchain
or database-specific behavior is required.
