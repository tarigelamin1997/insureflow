"""InsureFlow Phase 02 seed generator package.

Public entry point is `generate.py` (CLI). The package is importable so the unit tests in
`02-source-systems/tests/unit/test_seed_scenarios.py` can build a `Dataset` in-process and
assert on it without invoking `psql` or Docker.
"""
