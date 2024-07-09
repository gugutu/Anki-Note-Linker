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
    "showLinksPageInReviewerAutomatically": True,
    "splitRatio": "2:1",
    "splitRatioBetweenReviewerAndPanel": "4:1",
    "splitRatioBetweenLinksPageAndGraphPage": "1:1",
    "location": "right",
    "positionRelativeToReviewer": "right",
    "linkMaxLines": 5,
    "collapseClozeInLinksPage": True,
    "useHjpPreviewer": True,

    "shortcuts-copyNoteID": "Alt+Shift+C",
    "shortcuts-copyNoteLink": "Alt+Shift+L",
    "shortcuts-openNoteInNewWindow": "Alt+Shift+W",
    "shortcuts-insertLinkWithClipboardID": "Alt+Shift+V",
    "shortcuts-insertNewLink": "Alt+Shift+N",
    "shortcuts-insertLinkTemplate": "Alt+Shift+T",

    "globalGraph-defaultSearchText": "deck:current",
    "globalGraph-defaultHighlightFilter": "is:due",
    "globalGraph-defaultShowSingleNode": False,
    "globalGraph-defaultShowTags": False,
    "globalGraph-nodeColor": [57, 125, 237],
    "globalGraph-highlightedNodeColor": [244, 165, 0],
    "globalGraph-tagNodeColor": [127, 199, 132],
    "globalGraph-backgroundColor": [16, 16, 32]
}
# Check if there is an old version of the configuration;
# if it exists, convert it to the new version and delete the old version.
configTemp = mw.addonManager.getConfig(__name__)
if "shortcuts" in configTemp:
    configTemp["shortcuts-copyNoteID"] = (
        configTemp["shortcuts"].get("copyNoteID", defaultConfig["shortcuts-copyNoteID"]))
    configTemp["shortcuts-copyNoteLink"] = (
        configTemp["shortcuts"].get("copyNoteLink", defaultConfig["shortcuts-copyNoteLink"]))
    configTemp["shortcuts-openNoteInNewWindow"] = (
        configTemp["shortcuts"].get("openNoteInNewWindow", defaultConfig["shortcuts-openNoteInNewWindow"]))
    configTemp["shortcuts-insertLinkWithClipboardID"] = (
        configTemp["shortcuts"].get("insertLinkWithClipboardID", defaultConfig["shortcuts-insertLinkWithClipboardID"]))
    configTemp["shortcuts-insertNewLink"] = (
        configTemp["shortcuts"].get("insertNewLink", defaultConfig["shortcuts-insertNewLink"]))
    configTemp["shortcuts-insertLinkTemplate"] = (
        configTemp["shortcuts"].get("insertLinkTemplate", defaultConfig["shortcuts-insertLinkTemplate"]))
    del configTemp["shortcuts"]

if "globalGraph" in configTemp:
    configTemp["globalGraph-defaultSearchText"] = (
        configTemp["globalGraph"].get("defaultSearchText", defaultConfig["globalGraph-defaultSearchText"]))

    configTemp["globalGraph-defaultHighlightFilter"] = (
        configTemp["globalGraph"].get("defaultHighlightFilter", defaultConfig["globalGraph-defaultHighlightFilter"]))

    configTemp["globalGraph-defaultShowSingleNode"] = (
        configTemp["globalGraph"].get("defaultShowSingleNode", defaultConfig["globalGraph-defaultShowSingleNode"]))

    configTemp["globalGraph-nodeColor"] = (
        configTemp["globalGraph"].get("nodeColor", defaultConfig["globalGraph-nodeColor"]))

    configTemp["globalGraph-highlightedNodeColor"] = (
        configTemp["globalGraph"].get("highlightedNodeColor", defaultConfig["globalGraph-highlightedNodeColor"]))

    configTemp["globalGraph-backgroundColor"] = (
        configTemp["globalGraph"].get("graphBackgroundColor", defaultConfig["globalGraph-backgroundColor"]))

    del configTemp["globalGraph"]

if "Use the previewer of hjp-linkmaster if it is installed" in configTemp:
    configTemp["useHjpPreviewer"] = configTemp["Use the previewer of hjp-linkmaster if it is installed"]
    del configTemp["Use the previewer of hjp-linkmaster if it is installed"]

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
