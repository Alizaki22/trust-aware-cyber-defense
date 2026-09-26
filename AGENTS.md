# AGENTS.md — Instructions for AI Coding Agents

This file applies to **every AI coding agent** working in this repository, regardless of which tool is used (Claude, Codex, Antigravity, GitHub Copilot, Gemini, or any other). It is the common instruction manual all of them must follow.

## Documentation Is the Source of Truth

The Markdown documentation in this repository is the authoritative source of project requirements, architecture, scope, and approved decisions.

If a task request conflicts with the documented project scope, architecture, or approved decisions, the AI agent must **stop and ask the human team for clarification**.

AI agents must not silently override documented requirements based on assumptions, convenience, or a preferred implementation approach.

The relevant documentation must be updated whenever the team approves a change to the project scope or architecture.

## Before Any Task

Before performing any implementation task, an AI agent must:

1. Inspect the repository structure.
2. Read `docs/PROJECT_SCOPE.md`.
3. Read `docs/ARCHITECTURE.md`.
4. Read `docs/DECISIONS.md`.
5. Read `docs/RESEARCH.md`.
6. Read `docs/THREAT_MODEL.md`.
7. Read this file, `AGENTS.md`.
8. Read all relevant documentation under `docs/architecture/`, along with `docs/DECISIONS.md` and `docs/RESEARCH.md` and any other files in `docs/`.
9. Inspect relevant existing source code.
10. Inspect relevant existing tests.
11. Understand how the requested task fits into the existing project.

Only after completing these steps may an AI agent begin implementation.

If an AI agent does not understand something, it must **stop and ask the human team for clarification** rather than guessing.

## Understanding Summary

Before beginning a significant implementation task, the AI agent should provide a short summary containing:

1. What task it understands it is doing.
2. Which project requirements the task relates to.
3. Which documentation files it read.
4. Which files it expects to modify.
5. Whether the task requires a new architectural decision.

If the task requires a new architectural decision, the agent must **stop** and not implement the change until the human team approves it and records the decision in `docs/DECISIONS.md`.

## Core Rules

AI coding agents must:

- Respect `docs/PROJECT_SCOPE.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`.
- Keep the project simple — this is a student learning project, not an enterprise system.
- Follow the documented architecture rather than inventing a new one silently.
- Avoid unnecessary dependencies and frameworks.
- Avoid unrelated changes outside the scope of the current task.
- Add tests for important functionality.
- Explain significant changes in plain language.
- Verify generated code actually runs before claiming it works.
- Never claim tests passed without actually running them.
- Never invent research, citations, datasets, or experimental results.
- Never silently change the architecture.
- Never add new agents without an approved decision.
- Never expand project scope without an approved decision.
- Never describe or implement a real automated action against live infrastructure — all system actions are simulated (see `docs/DECISIONS.md`, D-011).
- Update documentation whenever an approved architectural change occurs.

If an AI agent believes a different architecture or approach would be better, it must **propose the change and explain why**, and wait for team approval — it must not implement the change silently.

## Git Workflow

- Stable branch: `main`. Integration branch: `development`.
- Normal flow: `feature/docs/research branch → Pull Request → development → testing → Pull Request → main`.
- **No AI agent may push directly to `main` or `development`, and no AI agent may merge directly into either.** All work happens on the assigned feature/docs/research branch and reaches `development` only through a reviewed Pull Request.
- **An AI agent must stay on the human team member's assigned branch for the task at hand.** Do not create, switch to, or push to a branch assigned to a different team member without being explicitly asked to.
- Branch naming should clearly describe purpose, e.g. `feature/detection-agent`, `docs/architecture`, `research/dataset`, `fix/...`, `experiment/...`.
- Commits must be small, focused, and descriptively named (e.g., `feat: implement detection agent`, `docs: update trust model`) — not vague messages like "stuff" or "updates."
- AI agents must not create commits claiming work that was not actually performed.
- **Git identity:** every commit must be authored under the human team member's own configured Git name and email, never as "Claude," "Codex," "Copilot," "Gemini," or any other AI/tool identity. If the local Git identity is not already configured correctly, the AI agent must stop and ask the team member for their name and email rather than guessing or leaving it as a generic default.

## Scope Control

Do not add, without an approved and documented decision: additional agents beyond Detection, Intelligence, Behavioral Analysis, and Verification; databases or vector databases not already justified in `docs/ARCHITECTURE.md`; RAG systems; blockchain; offensive security capabilities; enterprise infrastructure or microservices without a clear, documented educational reason; or any feature unrelated to the project's stated learning objectives in `docs/PROJECT_SCOPE.md`.

## Safety

This is an academic, defensive-only cybersecurity project. Use only authorized environments and synthetic or appropriately licensed data. Do not implement attacks against real systems. Any "response" or "action" the system produces must be simulated, not executed against live infrastructure.
