# Decisions

## Review loop and system cards (2026-11-01)
Tier 2 and 3 changes go through `/review-loop`: a general reviewer, one system reviewer per touched
card, and a separate fixer. Systems are cut by how they fail (money, access, state and timing,
dependencies, harness files). Rejected: one reviewer for everything, which missed system-specific
failures.

## Money in whole cents (2026-11-01)
Amounts are integers of cents, rounded only by `percentOf` (half up). Rejected: floats, which drift.
