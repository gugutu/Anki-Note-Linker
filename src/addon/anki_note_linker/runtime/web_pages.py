"""Build the HTML documents loaded into add-on WebViews."""

import json

import anki

from .configuration import config, getGraphZoomConfig
from .state import getWebFileLink, graph_html, links_html, newGraph_html


def _script(file_name: str) -> str:
    return f'<script src="{getWebFileLink(file_name)}"></script>'


def _language_and_context(context: str) -> str:
    return (
        f"<script>const ankiContext = {json.dumps(context)};</script>"
        f"<script>const ankiLanguage = {json.dumps(anki.lang.current_lang)};</script>" + _script("js/translation.js")
    )


def _math_assets() -> str:
    return f'<link rel="stylesheet" href="{getWebFileLink("dist/vendor/katex.css")}">' + _script("dist/vendor/katex.js")


def _graph_configuration(context: str) -> str:
    return (
        _language_and_context(context)
        + f"<script>const enableImagePreview = {json.dumps(config.get('enableImagePreview', True))};</script>"
        + f"<script>const enableSmoothGraphZoom = {json.dumps(config.get('enableSmoothGraphZoom', False))};</script>"
        + f"<script>const graphZoomConfig = {json.dumps(getGraphZoomConfig())};</script>"
        + _math_assets()
    )


def links_page(context: str) -> str:
    max_lines = int(config["linkMaxLines"])
    return (
        _language_and_context(context)
        + _math_assets()
        + f"<style>.link-button-text{{-webkit-line-clamp:{max_lines};line-clamp:{max_lines};}}</style>"
        + links_html
        + _script("dist/links.js")
    )


def new_graph_page(context: str) -> str:
    return (
        _graph_configuration(context)
        + _script("dist/vendor/d3.js")
        + _script("dist/vendor/pixi.js")
        + newGraph_html
        + _script("dist/new-graph.js")
    )


def legacy_graph_page(context: str) -> str:
    return (
        _graph_configuration(context)
        + _script("dist/vendor/d3.js")
        + _script("dist/vendor/force-graph.js")
        + _script("dist/graph-core.js")
        + graph_html
    )
