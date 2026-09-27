# Contributing

Contributions are welcome. Use Python 3.9+, [uv](https://docs.astral.sh/uv/), and npm. Node.js 24 is recommended to match CI; Node.js 22 must be 22.13 or newer.

## Quick Start

Run commands from the repository root:

```bash
uv sync --frozen --group dev
npm --prefix frontend ci
npm --prefix frontend run build
uv run --frozen python scripts/build_addon.py \
  --version development \
  --output dist/development.ankiaddon
```

The result is `dist/development.ankiaddon`. Installing it through Anki uses the official add-on ID (`1077002392`) and can replace the installed release.

For an isolated preview, close Anki, extract the archive into `addons21/Anki_Note_Linker_dev/`, and set its `manifest.json` package to `Anki_Note_Linker_dev` with a development name. Enable that copy and disable the official add-on so they do not run together. Use a test profile or back up your collection before testing.

When updating the development copy, preserve `meta.json`, `user_files/`, and any locally customized configuration, and remove obsolete code files. Rebuild after TypeScript or dependency changes, repackage after any source change, then update the development copy and restart Anki. The repository itself is not an installable add-on.

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
```

For browser-facing changes, install Chromium once, then run the browser tests:

```bash
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run test:browser
```

These checks do not launch Anki. For editor changes, also test the relevant actions in Anki with both the legacy and experimental editor, including HTML mode and IME input. The experimental editor is enabled under Preferences > Experiments.

CI runs on pull requests and pushes to `main`, and uploads a test package without publishing a release. Tag pushes publish releases; a separate manual workflow is also available.

## Notes

- Preserve existing user configuration and the `[title|nid1234567890123]` link format.
- Keep Anki-specific behavior in `src/addon/anki_note_linker/runtime/` where practical.
- Do not edit generated files under `src/addon/web/dist/`; rebuild them through the frontend project.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the project layout and compatibility details.
