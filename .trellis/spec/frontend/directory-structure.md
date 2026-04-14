# Directory Structure

> How frontend code is organized in this project.

---

## Overview

The frontend follows a highly componentized, flat structure based around Vite, shadcn/ui, and Zustand state management.

---

## Directory Layout

```text
web/
├── index.html
├── src/
│   ├── components/   # Chat components and shadcn/ui base elements
│   │   ├── ui/       # Pure shadcn/ui primitive un-modified components
│   ├── layouts/      # Macro structural page definitions (MainLayout)
│   ├── lib/          # API clients and pure UI utilities (Tailwind utils)
│   ├── store/        # Zustand global state vaults (useChatStore)
│   ├── types/        # Frontend API tracking contracts matching FastAPI
│   ├── App.tsx       # Root view assembler
│   ├── main.tsx      # Entrypoint
│   └── index.css     # Global variables and scrollbar themes
├── components.json   # shadcn-ui CLI manifest
├── tailwind.config.js
└── vite.config.ts    # Build & Proxy config
```

---

## Module Organization

- Keep generic and domain UI elements inside `components/` (e.g., `ChatArea`, `Sidebar`).
- Primitive, copy-paste components from `shadcn/ui` go strictly into `components/ui/`.
- Extract reusable logic containing network calls and side effects into the `store/`.
- Keep network fetch adapters separated in `lib/api.ts`.

---

## Naming Conventions

- Use **PascalCase** for React components (`MessageBubble.tsx`).
- Use **camelCase** for hooks, utilities, and stores (`useChatStore.ts`).
- **One Component Per File** is strictly favored, unless writing small, closely coupled internal components that aren't reused.

---

## Examples

- `src/components/ChatArea.tsx`: Dynamic message stream display module.
- `src/store/useChatStore.ts`: Global reactive conversation and SSE tracker.
- `src/lib/api.ts`: Typed API boundaries providing simple `fetch`/`SSE` wrapped interactions.
