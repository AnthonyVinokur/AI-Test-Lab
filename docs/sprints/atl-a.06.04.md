# ATL-A.06.04 — Evidence, Admission, and Run Binding

The append request must exactly match the authorization's evidence digest/type, producer,
run, admission decision, provenance reference, policy version, and upstream contract
versions. Any substitution fails closed with `evidence_binding_mismatch`.
