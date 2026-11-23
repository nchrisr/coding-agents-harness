# Rust pack

**Base:** Google Rust Style Guide, which builds on the official Rust style guide and API guidelines.
**Formatter:** `cargo fmt`. **Linter:** `cargo clippy --all-targets -- -D warnings`.
**Tests:** `cargo test`.

## Base style
**Google Rust Style Guide:** https://google.github.io/styleguide/rustguide.html, which defers to the
**Rust Style Guide** (https://doc.rust-lang.org/style-guide/) and the **Rust API Guidelines**
(https://rust-lang.github.io/api-guidelines/) and adds rules on API and implementation design.

The agent knows these guides from training and needs no internet to apply them; the link is for a
person, or an agent that wants the detail. The rules below are a summary in our own words, so the
pack works offline. **Project rules and the overrides in `rules/style.md` win** where they differ.

The rules that matter most (from the guides it builds on; read the Google guide for its additions):
- Layout is `rustfmt`'s job, with the project's `rustfmt.toml`, if any.
- `snake_case` for functions, variables and modules; `UpperCamelCase` for types and traits;
  `SCREAMING_SNAKE_CASE` for constants and statics.
- Conversions follow `as_` (cheap, borrowed), `to_` (costly), `into_` (consumes self).
- Public types implement the common traits that make sense (`Debug`, `Clone`, `PartialEq`, `Default`).
- Errors are typed (`Result<T, E>` with a meaningful `E`); a library never panics on bad input.
- Public items have doc comments, with an example where it helps.

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

## Dependencies (the `dependencies` card)
- **Lock file:** commit `Cargo.lock` for applications and binaries; build with `--locked`.
- **Vulnerability scan:** `scripts/deps-check.sh` (OSV-Scanner); `cargo audit` (RustSec) or
  `cargo deny check advisories sources` as a second opinion. `cargo deny` can also refuse crates from
  unknown registries or git sources.
- **Build-time code:** a crate's `build.rs` and procedural macros run on your machine at build time, and
  can't be switched off. So the stranger check matters more here: flag a new crate with a `build.rs` or
  a proc-macro, especially one with few users.
