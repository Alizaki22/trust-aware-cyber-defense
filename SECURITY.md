# Security Policy

## Project Context

This is an **academic, defensive-only** cybersecurity project developed by three university students. It is not a production system, does not process real security data in deployment, and **never executes real actions against live infrastructure** (see `docs/DECISIONS.md`, D-011).

## Scope

This security policy covers the project's codebase, documentation, and any data used during development and testing.

### In Scope

- Vulnerabilities in the project's Python codebase.
- Issues with how the system handles input data (e.g., prompt injection risks).
- Data handling problems (e.g., accidental exposure of API keys or credentials in the repository).
- Issues with dependencies or configurations that could compromise the development environment.

### Out of Scope

- Vulnerabilities in third-party LLM APIs or services the project connects to.
- Issues with the underlying operating system or hardware.
- Social engineering attacks against team members.
- Theoretical attacks against the trust model that are already documented as known limitations in `docs/THREAT_MODEL.md`.

## Reporting a Vulnerability

If you discover a security issue in this project:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Contact the project team directly through your university communication channels (email, messaging, etc.).
3. Include a description of the vulnerability, steps to reproduce, and potential impact.
4. The team will acknowledge receipt and work to address the issue.

Since this is a student project, response times depend on the team's academic schedule.

## Security Design Principles

The project follows these security principles (detailed in `docs/THREAT_MODEL.md`):

- **Simulated actions only.** The system never executes real cybersecurity responses against live infrastructure. All "actions" are simulated outputs for human review.
- **Defensive only.** No offensive security capabilities are implemented.
- **Input treated as untrusted.** Raw security events are treated as data to analyze, not as instructions to follow.
- **Separation of concerns.** Agent system prompts are kept separate from analyzed content to reduce prompt injection risk.
- **Verification cross-checks.** The Verification agent checks agent outputs against original evidence.
- **No secrets in code.** API keys, credentials, and sensitive configuration must not be committed to the repository. Use environment variables or local configuration files listed in `.gitignore`.

## Known Limitations

The following are documented, known limitations — not bugs:

- Prompt injection defenses are basic and academic in scope.
- Verification is not infallible and can itself be wrong.
- Trust scores are based on small sample sizes in demo scenarios.
- The fine-tuned model's behavior depends on the quality of training data.

See `docs/THREAT_MODEL.md` for the complete threat model and mitigations.

## Dependencies

The project uses third-party libraries (see `docs/DECISIONS.md`, D-007). Team members should:

- Keep dependencies updated to address known vulnerabilities.
- Review dependency licenses for compatibility with academic use.
- Avoid adding unnecessary dependencies.

## Data Handling

- Use only synthetic or appropriately licensed data for testing and training.
- Do not commit real, sensitive security data to the repository.
- Clearly label all synthetic data as synthetic.
- Follow dataset licensing terms as documented in `docs/DATASET.md`.
