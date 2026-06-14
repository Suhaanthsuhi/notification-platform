# Contributing to notifty

Thanks for your interest in improving notifty! This project is a reference
implementation of a distributed, event-driven notification pipeline, and
contributions that keep it clean, correct, and well-documented are very welcome.

## Getting set up

```bash
./setup.sh --with-infra   # venv + deps + .env + local Redis/Postgres in Docker
source .venv/bin/activate
```

See the [README](README.md) for the full local-development guide.

## Project conventions

- **Python 3.11**, `async`/`await` throughout for all I/O.
- The pipeline is built on three extension points — add features by registering,
  not by editing workers:
  - **Events** — add an `EventType`, register a Pydantic schema, a template, and
    translations (the startup contract validator enforces all four).
  - **Context loaders** — implement `BaseContextLoader` + `@register_loader`.
  - **Campaigns / segments** — implement the base class + the relevant decorator.
- Keep business logic out of the delivery worker; it is transport-only.

## Before opening a PR

```bash
python -m compileall -q app core contracts scripts
python -c "import app.engine.templates, contracts.events; \
  from contracts.validator import validate_event_contracts; validate_event_contracts()"
```

Both run in CI. Please make sure they pass locally and describe your change
clearly in the PR.

## Reporting issues

Open a GitHub issue with steps to reproduce, expected vs. actual behavior, and
relevant logs (with any secrets redacted).
