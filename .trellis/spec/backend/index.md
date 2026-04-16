# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | To fill |
| [Error Handling](./error-handling.md) | Error types, handling strategies | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Filled |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |
| [Research Agent Runtime](./research-agent-runtime.md) | Deep research workflow contracts, state, API, and checkpoints | Filled |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

## Pre-Development Checklist

For backend deep research work, read these files before editing code:

1. [Directory Structure](./directory-structure.md)
2. [Quality Guidelines](./quality-guidelines.md)
3. [Research Agent Runtime](./research-agent-runtime.md)
4. [Error Handling](./error-handling.md) when changing request validation or tool failure behavior
5. [Logging Guidelines](./logging-guidelines.md) when adding runtime instrumentation

## Quality Check

Before closing backend deep research work:

1. Check state changes stay inside graph nodes and pure logic stays in services
2. Check external side effects stay inside tools or runtime adapters
3. Check reports only cite source ids that exist in `sources`
4. Check research/chat entrypoints reject requests when required LLM capabilities are unavailable
5. Check pure service logic has unit coverage and the package compiles

**Language**: All documentation should be written in **English**.
