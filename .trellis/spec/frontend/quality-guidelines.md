# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

The frontend package owns its quality checks locally inside `web/`. Repository users should be able to discover and run them through `web/package.json` scripts without guessing which files need to be linted manually.

---

## Forbidden Patterns

### Ad-Hoc Lint Commands

Do not require contributors to remember file globs or one-off CLI flags that only exist in chat history.

Why:
- It makes quality checks inconsistent across sessions
- CI and local development drift quickly
- New contributors cannot discover the correct command path

Instead:
- Expose frontend lint through `npm run lint`
- Keep the file selection inside `web/eslint.config.js` and package scripts

### Blanket Rule Suppression

Do not add `eslint-disable` or `@ts-ignore` just to get a new lint setup passing unless there is a documented false positive with no practical alternative.

Why:
- It hides real issues
- It makes the new quality baseline unreliable

### Unused Placeholder Bindings for Object Omission

Avoid patterns like this when converting detail types into summary types:

```ts
const { largeField: _, otherField: __, ...summary } = value;
```

Why:
- `@typescript-eslint/no-unused-vars` flags the placeholder bindings
- The intent is less explicit than a direct summary shape

Instead, construct the target summary object explicitly.

---

## Required Patterns

### Frontend Lint Entry Point

Run frontend lint from `web/`:

```bash
npm run lint
```

The script must lint:
- `src/**/*.{ts,tsx}`
- frontend tool entry files such as `vite.config.ts` when they are part of the package

### Local Ownership of Frontend Quality Tooling

Keep frontend lint configuration in `web/eslint.config.js` and dependencies in `web/package.json`.

Why:
- The frontend is an independent Vite package
- Tooling stays close to the files it validates
- Backend Python tooling can evolve independently

### Explicit Summary Mapping

When frontend code derives a summary type from a richer API object, prefer explicit field mapping over omit-by-destructuring placeholders.

Good:

```ts
return {
  run_id: run.run_id,
  status: run.status,
  updated_at: run.updated_at,
};
```

This is easier to review and remains compatible with unused-variable lint rules.

---

## Testing Requirements

- Run `npm run lint`
- Run `npm run typecheck`
- Run `npm run test`

For frontend tooling changes, all three are required before closing the task.

---

## Code Review Checklist

- Can a contributor discover the frontend quality commands from `web/package.json`?
- Does `web/eslint.config.js` cover the files that actually matter in this package?
- Were lint fixes kept behavior-neutral?
- Are TypeScript and ESLint rules aligned instead of fighting each other?
- Did the change avoid suppressing lint rules just to get a passing result?
