# Architecture

The repository is a development workspace. `src/addon/` is the source tree that becomes the root of the generated `.ankiaddon` package.

## Project Layout

- `src/addon/__init__.py`: minimal Anki entry point.
- `src/addon/anki_note_linker/runtime/`: Anki and Qt integration.
- `src/addon/anki_note_linker/core/`: note links, summaries, bridge commands, and graph data without Anki dependencies.
- `src/addon/anki_note_linker/config/`: defaults, validation, and configuration migration.
- `frontend/`: TypeScript source, npm dependencies, build configuration, and browser tests.
- `src/addon/web/`: HTML templates and generated browser bundles. `graph.html` remains as the legacy renderer fallback.

Frontend dependencies come from `frontend/package-lock.json`. Builds are readable and unminified, with source maps for project code. Generated files under `src/addon/web/dist/` are not committed.

## Packaging

`scripts/build_addon.py` validates the source tree, adds `LICENSE` and a generated `manifest.json`, then creates a deterministic archive:

```text
src/addon/__init__.py         -> __init__.py
src/addon/config.json         -> config.json
src/addon/config.md           -> config.md
src/addon/anki_note_linker/   -> anki_note_linker/
src/addon/icons/              -> icons/
src/addon/web/                -> web/
LICENSE                       -> LICENSE
                               + generated manifest.json
```

## Compatibility

- Python code supports Python 3.9 and newer supported Anki versions.
- Configuration migrations preserve existing user values while converting legacy shapes and adding missing defaults.
- The `[title|nid1234567890123]` link format remains stable.

## Verification

CI runs Python and TypeScript unit tests, static checks, Playwright tests against the browser UI and WebGL graph, and deterministic build comparisons. Release candidates are verified manually in Anki because headless QtWebEngine behavior does not reliably represent the desktop application.
