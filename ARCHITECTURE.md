# Architecture

The repository is a development workspace. `src/addon/` is the source tree that becomes the root of the generated `.ankiaddon` package.

## Project Layout

- `src/addon/__init__.py`: minimal Anki entry point.
- `src/addon/anki_note_linker/runtime/`: Anki and Qt integration.
- `src/addon/anki_note_linker/core/`: note links, summaries, bridge commands, and graph data without Anki dependencies.
- `src/addon/anki_note_linker/config/`: defaults, validation, and configuration migration.
- `frontend/`: TypeScript source, npm dependencies, build configuration, and browser tests.
- `src/addon/web/`: HTML templates and generated browser bundles. `graph.html` remains as the legacy renderer fallback.

## Where to Make Changes

| Area | Main sources |
| --- | --- |
| Link parsing and note summaries | `core/links.py`, `core/summaries.py`, `frontend/src/links/`, `frontend/src/graph/content.ts` |
| Editor actions, panels, and windows | `runtime/editor_actions.py`, `runtime/editor_panels.py`, `runtime/editor_windows.py`; `frontend/src/editor/` for the new editor adapter |
| Graph behavior | `runtime/global_graph.py`, `frontend/src/graph/` |
| Configuration | `config/schema.py`, `config/migration.py`, `src/addon/config.json`, `frontend/src/config/`, `src/addon/web/config.html` |
| Translations | `runtime/i18n.py` for native widgets, `src/addon/web/js/translation.js` for web UI |

Python paths above are relative to `src/addon/anki_note_linker/`. Hook registration starts in `runtime/controller.py`; Python/web messages are parsed in `core/bridge.py` and handled in `runtime/bridge.py`.

Frontend dependencies come from `frontend/package-lock.json`. Builds are readable and unminified, with source maps for project code. Generated files under `src/addon/web/dist/` are not committed.

## Packaging

`scripts/build_addon.py` validates the source tree and generated frontend assets, places the contents of `src/addon/` at the archive root, and adds `LICENSE` and a generated `manifest.json`. The archive is deterministic and excludes development tooling. Build and preview instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Compatibility

- Python code targets Python 3.9 and newer.
- Editor integration selects legacy or new behavior by available APIs, not Anki version numbers. Legacy note/paste handling remains intact; the new editor uses its note ID and the TypeScript selection/menu adapter. Add-on-created edit/add windows still use the legacy editor.
- Configuration migrations preserve existing user values while converting legacy shapes and adding missing defaults.
- The `[title|nid1234567890123]` link format remains stable.

## Verification

CI tests Python 3.9 and 3.13, runs static checks, TypeScript unit tests and Chromium/Playwright tests, and compares frontend builds and add-on archives for deterministic output.

Runtime unit tests use Anki/Qt substitutes, and browser tests simulate editor APIs; neither runs real Anki. Mypy currently excludes `runtime/`. Release candidates still need manual Anki checks for editor behavior and window lifecycle, including both editor implementations when available.
