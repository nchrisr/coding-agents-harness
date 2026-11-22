# Python pack

**Base:** Google Python Style Guide. **Formatter and linter:** Ruff (`ruff format`, `ruff check`).
**Types:** Pyright or mypy in strict mode. Python won't stop a wrong type, so the type checker must.
**Tests:** pytest.

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
