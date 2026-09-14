# ATL-A.05.07 — Evidence Freshness and Replay Controls

Evaluates not-before, expiry, maximum age, and externally supplied replay status using
only the explicit evaluation time. No decision reads the process clock, and indeterminate
replay status fails closed.
