# Rust pack

**Base:** Google Rust Style Guide, which builds on the official Rust style guide and API guidelines.
**Formatter:** `cargo fmt`. **Linter:** `cargo clippy --all-targets -- -D warnings`.
**Tests:** `cargo test`.

## End-of-turn hook checks
`cargo clippy --all-targets -- -D warnings` · `cargo test`. File types: `\.(rs|toml)$`.

## Clippy settings that enforce the style rules
```toml
[lints.clippy]
unwrap_used = "deny"        # in library and production paths; allow in tests with #[cfg(test)]
expect_used = "warn"
panic = "warn"
indexing_slicing = "warn"
cast_possible_truncation = "warn"
undocumented_unsafe_blocks = "deny"
```
**Plain code and iterators:** Clippy prefers iterators (`needless_range_loop`), and in Rust that's
usually right. The override here: a chain of one or two steps is fine; past that, a `for` loop unless
the code is on a measured hot path. The reviewer checks this; don't silence Clippy to get loops.

## Classic traps (reviewer checklist)
- `unwrap()`/`expect()` in a path a user or the network can reach.
- `unsafe` without a `// SAFETY:` comment saying why it holds.
- `as` casts that truncate or change sign silently. Prefer `try_from`.
- Holding a lock across an `.await`. Blocking calls inside async code.
- Integer overflow: wraps in release builds. Use `checked_*` for money and counts.
- Errors swallowed with `let _ =` or `.ok()`.
