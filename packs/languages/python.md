# Python pack

**Base:** Google Python Style Guide. **Formatter and linter:** Ruff (`ruff format`, `ruff check`).
**Types:** Pyright or mypy in strict mode. Python won't stop a wrong type, so the type checker must.
**Tests:** pytest.

## Base style
**Google Python Style Guide:** https://google.github.io/styleguide/pyguide.html

The agent knows these guides from training and needs no internet to apply them; the link is for a
person, or an agent that wants the detail. The rules below are a summary in our own words, so the
pack works offline. **Project rules and the overrides in `rules/style.md` win** where they differ.

The rules that matter most:
- Import modules and packages, not individual functions or classes (`from x import y` only for modules).
- No mutable module-level state; constants are `UPPER_CASE` and never reassigned.
- Catch specific exceptions; never a bare `except:`. Don't use `assert` for checks that must run.
- Type annotations on every public function. Docstrings in Google style (`Args:`, `Returns:`, `Raises:`).
- `snake_case` for functions and variables, `CapWords` for classes, a leading `_` for internal names.
- Comprehensions only when trivially simple (one `for`, at most one `if`); otherwise a loop.
- Lambdas only as one-line arguments; anything longer gets a named function.
- No default argument that's mutable; use `None` and create it inside.

## End-of-turn hook checks
`ruff check .` · `pyright` (or `mypy .`) · `pytest -q`. File types that trigger it: `\.(py|toml)$`.

## Ruff settings that enforce the style rules
```toml
[tool.ruff.lint]
select = ["E", "F", "B", "UP", "SIM", "C4", "PL", "D", "S", "RET", "ARG", "PTH", "TRY"]
pydocstyle.convention = "google"
# The plain-code override: comprehensions are allowed only where trivially simple, so don't let
# flake8-comprehensions push loops into comprehensions.
ignore = ["C416", "C401", "C402", "C403", "C404", "PERF401", "SIM110"]
```
`PERF401` and `SIM110` *suggest* comprehensions and `any()`; ignoring them keeps plain loops. The
reviewer checks the rest of the override (no nested comprehensions, no clever one-liners).

## Classic traps (reviewer checklist)
- Mutable default arguments (`def f(x=[])`). Ruff `B006` catches it.
- Bare `except:` or `except Exception: pass` hiding failures.
- `None` used as a real value and as "unknown" in the same field.
- Float money. Use `Decimal` or integer minor units where amounts are compared or summed.
- Naive datetimes. Store and compare in UTC with `tzinfo`.
- `subprocess` with `shell=True`, `pickle`/`yaml.load` on untrusted data, `eval`. Ruff `S` rules.
- Async code calling blocking I/O.

## Dependencies (the `dependencies` card)
- **Lock file:** `uv.lock` (with `uv sync --locked`) or `poetry.lock`; with pip, pinned
  `requirements.txt` with hashes, installed with `pip install --require-hashes -r requirements.txt`.
- **Vulnerability scan:** `scripts/deps-check.sh` (OSV-Scanner); `pip-audit` is a second opinion.
- **Install-time code:** a source-only package runs its build code on install. Prefer wheels
  (`--only-binary=:all:` where every dependency has one), and treat a dependency with no wheel as a flag
  in the stranger check.
