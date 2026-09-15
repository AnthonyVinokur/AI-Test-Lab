# ATL-A.10.06 — Deterministic Status Resolution

Resolves active, suspended, revoked, expired, or superseded status only at an explicit caller-supplied
observation time. The fixed transition table rejects ambiguous same-time events and invalid recovery
from terminal states as `unknown`; it never reads the machine clock or silently skips bad transitions.
