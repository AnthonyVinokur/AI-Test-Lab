# ATL-A.07.09 — Failure and Outcome Normalization

Returns stable `PackageStatus` and `PackageReasonCode` values for expected build and
verification failures. Diagnostics are absent by default, preventing stack traces,
storage details, secrets, key material, and proprietary decisions from escaping.
