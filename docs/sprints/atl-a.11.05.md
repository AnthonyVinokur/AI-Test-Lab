# ATL-A.11.05 — Append-Only Merkle Transparency Log

Adds domain-separated leaf/internal-node hashing, deterministic roots, tree-size tracking, a replaceable
store protocol, and an in-memory reference store. Duplicate append is rejected; removal, mutation,
reordering, or historical insertion changes the committed root.
