# Contributing to Fine-Tuned Multi-Agent AI for Cyber Defense

Thank you for your interest in contributing to this project. This document describes our contribution process and guidelines.

## Project Context

This is a **university semester project** developed by three students. Contributions are expected primarily from team members, but this document also serves as a guide for anyone reviewing or building on this work.

## Before You Start

1. Read `docs/PROJECT_SCOPE.md` to understand the project scope.
2. Read `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` to understand the current architecture and approved decisions.
3. Read `AGENTS.md` for rules that apply to both human and AI contributors.
4. Check `docs/DECISIONS.md` for any pending decisions that may affect your work.

## Git Workflow

We follow the branching model described in `docs/DECISIONS.md` (D-009):

- **`main`** — Stable branch. No direct pushes or merges.
- **`develop`** — Integration branch. All feature work merges here first.
- **Feature branches** — Created from `develop` for each task.

### Branch Naming

Use descriptive branch names following these conventions:

| Prefix | Purpose | Example |
|---|---|---|
| `feature/` | New functionality | `feature/detection-agent` |
| `docs/` | Documentation updates | `docs/architecture` |
| `research/` | Research tasks | `research/dataset` |
| `fix/` | Bug fixes | `fix/trust-score-calculation` |
| `experiment/` | Experiments | `experiment/lora-vs-qlora` |

### Pull Request Process

1. Create a feature branch from `develop`.
2. Make your changes in small, focused commits.
3. Write descriptive commit messages (see Commit Messages below).
4. Open a Pull Request targeting `develop`.
5. Fill in the PR template (`.github/PULL_REQUEST_TEMPLATE.md`).
6. Wait for at least one team member to review.
7. Address review feedback.
8. Merge only after approval.

### Commit Messages

Use descriptive, conventional commit messages:

```
feat: implement detection agent prompt template
docs: update trust model documentation
fix: correct trust score calculation for edge case
test: add unit tests for verification agent
research: document dataset evaluation results
```

Avoid vague messages like "stuff", "updates", or "changes".

## Code Style

- **Language:** Python 3.11
- **Type hints:** Use type hints for function signatures.
- **Data validation:** Use Pydantic for data models.
- **Formatting:** Follow PEP 8 conventions.
- **Documentation:** Include docstrings for public functions and classes.
- **Tests:** Use pytest. Add tests for important functionality.

## Scope Control

Do **not** add without a team-approved decision recorded in `docs/DECISIONS.md`:

- Additional agents beyond Detection, Intelligence, Behavioral Analysis, and Verification.
- Databases or vector databases not already justified.
- RAG systems, blockchain, or offensive security capabilities.
- Enterprise infrastructure or microservices.
- Any feature outside `docs/PROJECT_SCOPE.md`.

If you believe a different approach would be better, **propose the change and explain why** — do not implement it silently.

## Safety Rules

- This is a **defensive-only** project. No offensive security capabilities.
- All system actions are **simulated only** — never real actions against live infrastructure.
- Use only authorized environments and synthetic or appropriately licensed data.
- Do not implement attacks against real systems.

## Reporting Issues

Use the issue templates in `.github/ISSUE_TEMPLATE/` for:

- Bug reports
- Feature requests
- Documentation improvements

## Questions

If you are unsure about anything — scope, architecture, implementation approach — **ask the team** rather than guessing. This applies equally to human and AI contributors.
