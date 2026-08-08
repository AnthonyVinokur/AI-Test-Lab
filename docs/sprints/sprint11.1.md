Sprint 11.1 — Evaluation Profile Catalog

Goal
Provide built-in evaluation profiles selectable by name.

Built-in profiles
- default
- fast-ci
- deep-quality
- rag
- enterprise

Implementation
- Added profile catalog discovery
- Added name-to-path resolution
- Preserved explicit custom profile paths
- Integrated catalog resolution into existing evaluation_config loader
- Added catalog and loader regression tests

CLI
python main.py --evaluation-profile fast-ci

Validation
133 tests passed
CLI smoke test confirmed fast-ci loads successfully

Result
Users can now select built-in evaluation strategies without supplying full file paths.