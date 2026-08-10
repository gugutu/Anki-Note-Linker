# Contributing

Contributions are welcome. The project uses Python 3.9+, [uv](https://docs.astral.sh/uv/), Node.js 22+, and npm.

## Setup

```bash
uv sync --frozen --group dev
npm --prefix frontend ci
```

## Checks

Run the checks relevant to your change:

```bash
# Python
uv run --frozen --group dev python -m pytest -q
uv run --frozen --group dev ruff check .
uv run --frozen --group dev ruff format --check src/addon/anki_note_linker scripts tests
uv run --frozen --group dev mypy

# Frontend
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build

# Installable package (after the frontend build)
uv run --frozen python scripts/build_addon.py \
  --version development \
  --output dist/development.ankiaddon
```

Browser tests run automatically in CI.

## Notes

- Preserve existing user configuration and the `[title|nid1234567890123]` link format.
- Keep Anki-specific behavior in `src/addon/anki_note_linker/runtime/` where practical.
- Do not edit generated files under `src/addon/web/dist/`; rebuild them through the frontend project.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the project layout and compatibility details.
