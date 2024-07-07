"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""
import json
import re
from typing import Any

import anki
from aqt import QWidget, QVBoxLayout, Qt, gui_hooks
from aqt import mw
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from .translation import getTr
from .state import config_html, getWebFileLink

defaultConfig = {
    "showLinksPageAutomatically": True,
    "showGraphPageAutomatically": True,
    "splitRatio": "2:1",
    "splitRatioBetweenLinksPageAndGraphPage": "1:1",
    "location": "right",
    "linkMaxLines": 5,
    "collapseClozeInLinksPage": True,
    "shortcuts": {
        "copyNoteID": "Alt+Shift+C",
        "copyNoteLink": "Alt+Shift+L",
        "openNoteInNewWindow": "Alt+Shift+W",
        "insertLinkWithClipboardID": "Alt+Shift+V",
        "insertNewLink": "Alt+Shift+N",
        "insertLinkTemplate": "Alt+Shift+T"
    },
    "globalGraph": {
        "defaultSearchText": "deck:current",
        "defaultHighlightFilter": "is:due",
        "defaultShowSingleNode": False,
        "nodeColor": [57, 125, 237],
        "highlightedNodeColor": [244, 165, 0],
        "graphBackgroundColor": [16, 16, 32]
    },
    "Use the previewer of hjp-linkmaster if it is installed": True
}
configTemp = mw.addonManager.getConfig(__name__)
configTemp["shortcuts"].setdefault("copyNoteID", defaultConfig["shortcuts"]["copyNoteID"])
configTemp["shortcuts"].setdefault("copyNoteLink", defaultConfig["shortcuts"]["copyNoteLink"])
configTemp["shortcuts"].setdefault("openNoteInNewWindow", defaultConfig["shortcuts"]["openNoteInNewWindow"])
configTemp["shortcuts"].setdefault("insertLinkWithClipboardID", defaultConfig["shortcuts"]["insertLinkWithClipboardID"])
configTemp["shortcuts"].setdefault("insertNewLink", defaultConfig["shortcuts"]["insertNewLink"])
configTemp["shortcuts"].setdefault("insertLinkTemplate", defaultConfig["shortcuts"]["insertLinkTemplate"])
configTemp["globalGraph"].setdefault("defaultSearchText", defaultConfig["globalGraph"]["defaultSearchText"])
configTemp["globalGraph"].setdefault("defaultHighlightFilter", defaultConfig["globalGraph"]["defaultHighlightFilter"])
configTemp["globalGraph"].setdefault("defaultShowSingleNode", defaultConfig["globalGraph"]["defaultShowSingleNode"])
configTemp["globalGraph"].setdefault("nodeColor", defaultConfig["globalGraph"]["nodeColor"])
configTemp["globalGraph"].setdefault("highlightedNodeColor", defaultConfig["globalGraph"]["highlightedNodeColor"])
configTemp["globalGraph"].setdefault("graphBackgroundColor", defaultConfig["globalGraph"]["graphBackgroundColor"])
mw.addonManager.writeConfig(__name__, configTemp)
config = mw.addonManager.getConfig(__name__)


class ConfigView(QWidget):
    configView = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle(getTr("Anki-Note-Linker Config"))
        restoreGeom(self, "AnkiNoteLinkerConfig", default_size=(530, 550))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(530)
        outerLayout = QVBoxLayout()
        self.setLayout(outerLayout)
        self.web = AnkiWebView(self, title="GlobalGraph")
        gui_hooks.webview_did_receive_js_message.append(self.handlePycmd)
        self.web.stdHtml(
            f'<script>const ankiLanguage = "{anki.lang.current_lang}"</script>'
            f'<script>const defaultConfig = {json.dumps(defaultConfig, default=lambda o: o.__dict__)}</script>'
            f'<script>const userConfig = {json.dumps(config, default=lambda o: o.__dict__)}</script>'
            f'<script src="{getWebFileLink("js/translation.js")}"></script>' + config_html
        )
        self.web.set_bridge_command(lambda s: s, self)
        outerLayout.addWidget(self.web)
        outerLayout.setContentsMargins(0, 0, 0, 0)
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
        gui_hooks.webview_did_receive_js_message.remove(self.handlePycmd)
        saveGeom(self, "AnkiNoteLinkerConfig")
        ConfigView.configView = None
        event.accept()

    def handlePycmd(self, handled: tuple[bool, Any], message, context: Any):
        if context != self:
            return handled
        elif message == "AnkiNoteLinker-config-cancel":
            self.close()
            return True, None
        elif re.match(r'AnkiNoteLinker-config-ok.*}', message):
            global config
            config.update(json.loads(message[24:]))
            mw.addonManager.writeConfig(__name__, config)
            self.close()
            return True, None
        else:
            return handled


mw.addonManager.setConfigAction(__name__, ConfigView.openConfigView)
