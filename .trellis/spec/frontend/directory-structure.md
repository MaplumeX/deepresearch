# Directory Structure

> How frontend code is organized in this project.

---

## Overview

<!--
Document your project's frontend directory structure here.

Questions to answer:
- Where do components live?
- How are features/modules organized?
- Where are shared utilities?
- How are assets organized?
-->

(To be filled by the team)

---

## Directory Layout

```text
web/
├── index.html
├── package.json
├── src/
│   ├── app/          # Router + providers
│   ├── components/   # Reusable UI building blocks
│   ├── hooks/        # React Query + SSE hooks
│   ├── lib/          # API clients and pure UI utilities
│   ├── pages/        # Route-level screens
│   ├── test/         # Test setup
│   ├── types/        # Frontend API contracts
│   ├── main.tsx
│   └── styles.css
└── vite.config.ts
```

---

## Module Organization

- Keep route-level orchestration inside `pages/`
- Extract reusable fetch/query logic into `hooks/` and `lib/`
- Put backend contract mirrors in `types/`; do not scatter status strings across components
- Keep styling centralized in `styles.css` until repeated patterns justify splitting files

---

## Naming Conventions

- Use PascalCase for React components and pages
- Use camelCase for hooks and utility files
- Keep one responsibility per file where practical

---

## Examples

- `src/pages/RunDetailPage.tsx`: route assembly for detail view
- `src/hooks/useRunEvents.ts`: SSE subscription + cache sync
- `src/lib/api.ts`: typed API client boundary
