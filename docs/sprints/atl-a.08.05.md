# ATL-A.08.05 — Deterministic Retention Evaluation

Evaluates policy activation and evidence retention against one explicitly supplied,
timezone-aware trusted time. The engine never reads a hidden system clock. Retention is
defined per evidence type and uses a precise, repeatable expiration boundary.
