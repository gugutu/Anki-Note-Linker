"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""

import json
import re
from typing import Any

import anki

try:
    from anki.utils import is_mac
except ImportError:
    from anki.utils import isMac as is_mac
from aqt import Qt, QVBoxLayout, QWidget, gui_hooks, mw
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from ..config.migration import migrate_config
from ..config.schema import GRAPH_ZOOM_SETTINGS, default_config, graph_zoom_config
from .i18n import getTr
from .lifecycle import cleanup_webview, enable_immediate_profile_close, remove_hook_safely
from .state import config_html, getWebFileLink

defaultConfig = default_config(is_mac)
graphZoomConfigSpec = {
    config_key: {
        "key": setting.runtime_key,
        "default": setting.default,
        "min": setting.minimum,
        "max": setting.maximum,
    }
    for config_key, setting in GRAPH_ZOOM_SETTINGS.items()
}


def getGraphZoomConfig() -> dict[str, float]:
    return graph_zoom_config(config)


raw_config = mw.addonManager.getConfig(__name__) or {}
config = migrate_config(raw_config, defaultConfig)
if config != raw_config:
    mw.addonManager.writeConfig(__name__, config)


class ConfigView(QWidget):
    configView = None

    def __init__(self):
        super().__init__()
        self._closed = False
        self.setWindowTitle(getTr("Anki-Note-Linker Config"))
        restoreGeom(self, "AnkiNoteLinkerConfig", default_size=(530, 550))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(530)
        outerLayout = QVBoxLayout()
        self.setLayout(outerLayout)
        self.web = AnkiWebView(self, title="AnkiNoteLinkerConfig")
        gui_hooks.webview_did_receive_js_message.append(self.handlePycmd)
        self.web.stdHtml(
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f"<script>const isMac = {json.dumps(is_mac)}</script>"
            f"<script>const defaultConfig = {json.dumps(defaultConfig, default=lambda o: o.__dict__)}</script>"
            f"<script>const userConfig = {json.dumps(config, default=lambda o: o.__dict__)}</script>"
            f'<script src="{getWebFileLink("js/translation.js")}"></script>'
            + config_html
            + f'<script src="{getWebFileLink("dist/config.js")}"></script>'
        )
        self.web.set_bridge_command(lambda s: s, self)
        outerLayout.addWidget(self.web)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        enable_immediate_profile_close(self)
        self.activateWindow()
        self.show()

    @staticmethod
    def openConfigView():
        if ConfigView.configView is None:
            ConfigView.configView = ConfigView()
        else:
            ConfigView.configView.showNormal()
            ConfigView.configView.activateWindow()

    def closeEvent(self, event):
        if self._closed:
            event.accept()
            return
        self._closed = True
        remove_hook_safely(gui_hooks.webview_did_receive_js_message, self.handlePycmd)
        saveGeom(self, "AnkiNoteLinkerConfig")
        cleanup_webview(self, "web")
        ConfigView.configView = None
        event.accept()

    def handlePycmd(self, handled: tuple[bool, Any], message, context: Any):
        if self._closed or context != self:
            return handled
        elif message == "AnkiNoteLinker-config-cancel":
            self.close()
            return True, None
        elif re.match(r"AnkiNoteLinker-config-ok.*}", message):
            global config
            config.update(json.loads(message[24:]))
            mw.addonManager.writeConfig(__name__, config)
            self.close()
            return True, None
        else:
            return handled


mw.addonManager.setConfigAction(__name__, ConfigView.openConfigView)
