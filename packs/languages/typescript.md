# TypeScript and JavaScript pack

**Base:** Google TypeScript Style Guide (JavaScript: Google JavaScript Style Guide).
**Formatter:** Prettier. **Linter:** ESLint (flat config) with `typescript-eslint` strict, run with
`--max-warnings=0`. **Types:** `tsc --noEmit` with `strict: true`. JavaScript-only projects add
`// @ts-check` or JSDoc types where practical. **Tests:** Vitest (or the project's runner).

## End-of-turn hook checks
`tsc --noEmit` · tests. File types that trigger it: `\.(ts|tsx|js|jsx|mjs|cjs|json)$`.
Lint and build are slower: before committing.

## ESLint rules that enforce the style rules
```js
'no-nested-ternary': 'error',
'@typescript-eslint/no-explicit-any': 'error',
'@typescript-eslint/no-floating-promises': 'error',
'@typescript-eslint/switch-exhaustiveness-check': 'error',
'@typescript-eslint/strict-boolean-expressions': 'warn',
```
The plain-loop override has no clean lint rule; the reviewer checks it (more than two chained
`filter`/`map`/`reduce` steps, or a `reduce` building an object, becomes a loop).

## Classic traps (reviewer checklist)
- `any`, `as` casts and `!` non-null assertions hiding a real `undefined`.
- Floating promises: an `async` call with no `await`, so its failure vanishes.
- **What crosses from server to browser.** In React server/client splits (Next.js and similar), every
  prop of a client component ships to every browser, rendered or not.
- `==` and truthiness: `0` and `''` are falsy, so `if (price)` treats a zero price as missing.
- Floating-point money: round at the edges, never compare with `===`.
- Dates: `new Date('2026-01-02')` is UTC midnight, which shows as the day before in the Americas.
- Every async button: what happens on a second click while the first is running? (state and timing)
