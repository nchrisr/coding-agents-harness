# Code style

## Base
Follow Google's style guide for the language, unless the project already has its own:
- Python: https://google.github.io/styleguide/pyguide.html
- TypeScript: https://google.github.io/styleguide/tsguide.html
- JavaScript: https://google.github.io/styleguide/jsguide.html
- Rust: https://google.github.io/styleguide/rustguide.html (it builds on the official Rust style
  guide and rustfmt)

Formatting is the formatter's job. Don't hand-format and don't argue with it.

## The owner's overrides
These win over the base guide.

1. **Plain code over clever syntax.** Write code a tired reader can follow on the first pass.
   - Filtering, searching and building a list: an expanded `for` or `while` loop, not a
     comprehension, a chain of `filter`/`map`/`reduce`, or a one-line trick.
   - **Allowed:** a built-in that is plainly the right tool (`sorted(items, key=...)`,
     `array.sort((a, b) => ...)`, `vec.sort_by_key(...)`), and a compact form with a measured speed
     gain, with a comment saying so.
   - **Rust:** iterator chains are idiomatic and sometimes optimise better than loops. Keep a chain
     to one or two steps; past that, use a loop unless it's on a measured hot path.
   - No nested ternaries. `if`/`else` for any choice between actions.
2. **Unknown is explicit.** Model "unknown" as `None`/`null`/`Option` and make callers handle it.
   Never a plausible default in its place.
3. **Name for how data is got:** `fetch…` reads a database or service, `load…` assembles from
   `fetch…` calls, `get…` reads what's already in hand.
4. **Comments say why, in the present tense.** History goes in commit messages and docs.

## Enforce by program, not prose
Turn each rule a linter can check into a linter rule (see the language pack). Keep in prose only what
no tool can check, and have the reviewer check that.
