"""
AGPL3 LICENSE
Author Wang Rui <https://github.com/gugutu>
"""

import re
from aqt import QColor, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QHBoxLayout, QColorDialog, Qt, QCheckBox, \
    QComboBox, QRegularExpressionValidator, QRegularExpression, QFormLayout, QFont, QScrollArea, QIntValidator
from aqt import mw, qconnect
from aqt.utils import restoreGeom, saveGeom, tooltip
from .translation import getTr

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
        "nodeColor": [57, 125, 237],
        "highlightedNodeColor": [244, 165, 0]
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
configTemp["globalGraph"].setdefault("nodeColor", defaultConfig["globalGraph"]["nodeColor"])
configTemp["globalGraph"].setdefault("highlightedNodeColor", defaultConfig["globalGraph"]["highlightedNodeColor"])
mw.addonManager.writeConfig(__name__, configTemp)
config = mw.addonManager.getConfig(__name__)


class ConfigView(QWidget):
    configView = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle(getTr("Anki-Note-Linker Config"))
        restoreGeom(self, "AnkiNoteLinkerConfig", default_size=(500, 550))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(500)
        outerLayout = QVBoxLayout()
        self.setLayout(outerLayout)
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        contentWidget = QWidget()
        buttonWidget = QWidget()
        buttonLayout = QHBoxLayout()
        buttonWidget.setLayout(buttonLayout)
        outerLayout.addWidget(scrollArea)
        outerLayout.addWidget(buttonWidget)

        defaultButton = QPushButton(getTr('Restore Defaults'))
        qconnect(defaultButton.clicked, self.restoreDefaults)
        cancelButton = QPushButton(getTr('Cancel'))
        qconnect(cancelButton.clicked, self.close)
        okButton = QPushButton(getTr('OK'))
        qconnect(okButton.clicked, self.saveConfig)
        okButton.setStyleSheet("""QPushButton {border: 1px solid blue;}""")
        buttonLayout.addWidget(defaultButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(cancelButton)
        buttonLayout.addWidget(okButton)

        layout = QFormLayout()
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        contentWidget.setLayout(layout)

        lab1 = QLabel(getTr('Basic'))
        lab1.setFont(QFont("Sans-Serif", 15, 75))
        layout.addRow(lab1)

        self.showLinksPageAutomatically_CheckBox = QCheckBox()
        self.showLinksPageAutomatically_CheckBox.setChecked(config["showLinksPageAutomatically"])
        layout.addRow(getTr('Automatically show links panel when entering editor') + ':',
                      self.showLinksPageAutomatically_CheckBox)

        self.showGraphPageAutomatically_CheckBox = QCheckBox()
        self.showGraphPageAutomatically_CheckBox.setChecked(config["showGraphPageAutomatically"])
        layout.addRow(getTr('Automatically show graph panel when entering editor') + ':',
                      self.showGraphPageAutomatically_CheckBox)

        self.collapseClozeInLinksPage_CheckBox = QCheckBox()
        self.collapseClozeInLinksPage_CheckBox.setChecked(config["collapseClozeInLinksPage"])
        layout.addRow(getTr('Collapse cloze in links panel') + ':', self.collapseClozeInLinksPage_CheckBox)

        self.useHjpPreviewer_CheckBox = QCheckBox()
        self.useHjpPreviewer_CheckBox.setChecked(config["Use the previewer of hjp-linkmaster if it is installed"])
        layout.addRow(getTr('If the "hjp-linkmaster" add-on is installed, use its previewer') + ':',
                      self.useHjpPreviewer_CheckBox)

        self.location_ComboBox = QComboBox()
        self.location_ComboBox.addItem(getTr('left'))
        self.location_ComboBox.addItem(getTr('right'))
        self.location_ComboBox.setCurrentText(getTr(config["location"]))
        layout.addRow(getTr('The position of links/graph panel relative to the editor') + ':', self.location_ComboBox)

        self.splitRatio_LineEdit = QLineEdit(config["splitRatio"])
        self.splitRatio_LineEdit.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d+:\d+")))
        layout.addRow(getTr('Split ratio between editor and panels') + ':', self.splitRatio_LineEdit)

        self.splitRatioBetweenLinksPageAndGraphPage_LineEdit = QLineEdit(
            config["splitRatioBetweenLinksPageAndGraphPage"])
        self.splitRatioBetweenLinksPageAndGraphPage_LineEdit.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d+:\d+")))
        layout.addRow(getTr('Split ratio between links panel and graph panel') + ':',
                      self.splitRatioBetweenLinksPageAndGraphPage_LineEdit)

        self.linkMaxLines_LineEdit = QLineEdit(str(config["linkMaxLines"]))
        self.linkMaxLines_LineEdit.setValidator(QIntValidator(1, 999))
        layout.addRow(getTr('Max displayed lines per link in links panel') + ':', self.linkMaxLines_LineEdit)

        lab2 = QLabel(getTr('Global Relationship Graph'))
        lab2.setFont(QFont("Sans-Serif", 15, 75))
        layout.addRow(lab2)

        self.globalGraph_defaultSearchText_LineEdit = QLineEdit(config["globalGraph"]["defaultSearchText"])
        layout.addRow(getTr('Default search text') + ':', self.globalGraph_defaultSearchText_LineEdit)

        self.globalGraph_defaultHighlightFilter_LineEdit = QLineEdit(config["globalGraph"]["defaultHighlightFilter"])
        layout.addRow(getTr('Default filter text for highlighted nodes') + ':',
                      self.globalGraph_defaultHighlightFilter_LineEdit)

        self.globalGraph_nodeColor_Button = QPushButton()
        qconnect(self.globalGraph_nodeColor_Button.clicked, self.changeNodeColor)
        self.globalGraph_nodeColor_Button.qColor = QColor.fromRgb(*config["globalGraph"]["nodeColor"])
        self.globalGraph_nodeColor_Button.setStyleSheet(
            'QPushButton{background:' + self.globalGraph_nodeColor_Button.qColor.name() + ';}')
        layout.addRow(getTr('Node color') + ':', self.globalGraph_nodeColor_Button)

        self.globalGraph_highlightedNodeColor_Button = QPushButton()
        qconnect(self.globalGraph_highlightedNodeColor_Button.clicked, self.changeHighlightedNodeColor)
        self.globalGraph_highlightedNodeColor_Button.qColor = QColor.fromRgb(
            *config["globalGraph"]["highlightedNodeColor"])
        self.globalGraph_highlightedNodeColor_Button.setStyleSheet(
            'QPushButton{background:' + self.globalGraph_highlightedNodeColor_Button.qColor.name() + ';}')
        layout.addRow(getTr('Highlighted node color') + ':', self.globalGraph_highlightedNodeColor_Button)

        lab2 = QLabel(getTr('Shortcut keys'))
        lab2.setFont(QFont("Sans-Serif", 15, 75))
        layout.addRow(lab2)

        self.shortcuts_copyNoteID_LineEdit = QLineEdit(config["shortcuts"]["copyNoteID"])
        layout.addRow(getTr('Copy current note ID') + ':', self.shortcuts_copyNoteID_LineEdit)

        self.shortcuts_copyNoteLink_LineEdit = QLineEdit(config["shortcuts"]["copyNoteLink"])
        layout.addRow(getTr('Copy current note link') + ':', self.shortcuts_copyNoteLink_LineEdit)

        self.shortcuts_openNoteInNewWindow_LineEdit = QLineEdit(config["shortcuts"]["openNoteInNewWindow"])
        layout.addRow(getTr('Open current note in new window') + ':', self.shortcuts_openNoteInNewWindow_LineEdit)

        self.shortcuts_insertLinkWithClipboardID_LineEdit = QLineEdit(config["shortcuts"]["insertLinkWithClipboardID"])
        layout.addRow(getTr('Insert link with copied note ID') + ':', self.shortcuts_insertLinkWithClipboardID_LineEdit)

        self.shortcuts_insertNewLink_LineEdit = QLineEdit(config["shortcuts"]["insertNewLink"])
        layout.addRow(getTr('Insert new link') + ':', self.shortcuts_insertNewLink_LineEdit)

        self.shortcuts_insertLinkTemplate_LineEdit = QLineEdit(config["shortcuts"]["insertLinkTemplate"])
        layout.addRow(getTr('Insert link template') + ':', self.shortcuts_insertLinkTemplate_LineEdit)
        scrollArea.setWidget(contentWidget)
        self.activateWindow()
        self.show()

    def restoreDefaults(self):
        self.showLinksPageAutomatically_CheckBox.setChecked(defaultConfig["showLinksPageAutomatically"])
        self.showGraphPageAutomatically_CheckBox.setChecked(defaultConfig["showGraphPageAutomatically"])
        self.collapseClozeInLinksPage_CheckBox.setChecked(defaultConfig["collapseClozeInLinksPage"])
        self.useHjpPreviewer_CheckBox.setChecked(
            defaultConfig["Use the previewer of hjp-linkmaster if it is installed"])
        self.location_ComboBox.setCurrentText(getTr(defaultConfig["location"]))
        self.splitRatio_LineEdit.setText(defaultConfig["splitRatio"])
        self.splitRatioBetweenLinksPageAndGraphPage_LineEdit.setText(
            defaultConfig["splitRatioBetweenLinksPageAndGraphPage"])
        self.linkMaxLines_LineEdit.setText(str(defaultConfig["linkMaxLines"]))
        self.globalGraph_defaultSearchText_LineEdit.setText(defaultConfig["globalGraph"]["defaultSearchText"])
        self.globalGraph_defaultHighlightFilter_LineEdit.setText(defaultConfig["globalGraph"]["defaultHighlightFilter"])
        self.globalGraph_nodeColor_Button.qColor = QColor.fromRgb(*defaultConfig["globalGraph"]["nodeColor"])
        self.globalGraph_nodeColor_Button.setStyleSheet(
            'QPushButton{background:' + self.globalGraph_nodeColor_Button.qColor.name() + ';}')
        self.globalGraph_highlightedNodeColor_Button.qColor = QColor.fromRgb(
            *defaultConfig["globalGraph"]["highlightedNodeColor"])
        self.globalGraph_highlightedNodeColor_Button.setStyleSheet(
            'QPushButton{background:' + self.globalGraph_highlightedNodeColor_Button.qColor.name() + ';}')
        self.shortcuts_copyNoteID_LineEdit.setText(defaultConfig["shortcuts"]["copyNoteID"])
        self.shortcuts_copyNoteLink_LineEdit.setText(defaultConfig["shortcuts"]["copyNoteLink"])
        self.shortcuts_openNoteInNewWindow_LineEdit.setText(defaultConfig["shortcuts"]["openNoteInNewWindow"])
        self.shortcuts_insertLinkWithClipboardID_LineEdit.setText(
            defaultConfig["shortcuts"]["insertLinkWithClipboardID"])
        self.shortcuts_insertNewLink_LineEdit.setText(defaultConfig["shortcuts"]["insertNewLink"])
        self.shortcuts_insertLinkTemplate_LineEdit.setText(defaultConfig["shortcuts"]["insertLinkTemplate"])

    def saveConfig(self):
        if (not re.match(r'^\d+:\d+$', self.splitRatio_LineEdit.text()) or
                not re.match(r'^\d+:\d+$', self.splitRatioBetweenLinksPageAndGraphPage_LineEdit.text())):
            tooltip(getTr('The format of "split ratio" is incorrect'))
            return
        if self.linkMaxLines_LineEdit.text() == '' or int(self.linkMaxLines_LineEdit.text()) == 0:
            self.linkMaxLines_LineEdit.setText(str(defaultConfig["linkMaxLines"]))

        config["showLinksPageAutomatically"] = self.showLinksPageAutomatically_CheckBox.isChecked()
        config["showGraphPageAutomatically"] = self.showGraphPageAutomatically_CheckBox.isChecked()
        config["collapseClozeInLinksPage"] = self.collapseClozeInLinksPage_CheckBox.isChecked()
        config["Use the previewer of hjp-linkmaster if it is installed"] = self.useHjpPreviewer_CheckBox.isChecked()
        config["location"] = 'left' if self.location_ComboBox.currentIndex() == 0 else 'right'
        config["splitRatio"] = self.splitRatio_LineEdit.text()
        config["splitRatioBetweenLinksPageAndGraphPage"] = self.splitRatioBetweenLinksPageAndGraphPage_LineEdit.text()
        config["linkMaxLines"] = int(self.linkMaxLines_LineEdit.text())
        config["globalGraph"]["defaultSearchText"] = self.globalGraph_defaultSearchText_LineEdit.text()
        config["globalGraph"]["defaultHighlightFilter"] = self.globalGraph_defaultHighlightFilter_LineEdit.text()
        color = self.globalGraph_nodeColor_Button.qColor
        config["globalGraph"]["nodeColor"] = [color.red(), color.green(), color.blue()]
        color = self.globalGraph_highlightedNodeColor_Button.qColor
        config["globalGraph"]["highlightedNodeColor"] = [color.red(), color.green(), color.blue()]
        config["shortcuts"]["copyNoteID"] = self.shortcuts_copyNoteID_LineEdit.text()
        config["shortcuts"]["copyNoteLink"] = self.shortcuts_copyNoteLink_LineEdit.text()
        config["shortcuts"]["openNoteInNewWindow"] = self.shortcuts_openNoteInNewWindow_LineEdit.text()
        config["shortcuts"]["insertLinkWithClipboardID"] = self.shortcuts_insertLinkWithClipboardID_LineEdit.text()
        config["shortcuts"]["insertNewLink"] = self.shortcuts_insertNewLink_LineEdit.text()
        config["shortcuts"]["insertLinkTemplate"] = self.shortcuts_insertLinkTemplate_LineEdit.text()
        mw.addonManager.writeConfig(__name__, config)
        self.close()

    def changeNodeColor(self):
        color = QColorDialog.getColor(self.globalGraph_nodeColor_Button.qColor)
        if color is None or color.name() == "#000000":
            return
        self.globalGraph_nodeColor_Button.qColor = color
        self.globalGraph_nodeColor_Button.setStyleSheet('QPushButton{background:' + color.name() + ';}')

    def changeHighlightedNodeColor(self):
        color = QColorDialog.getColor(self.globalGraph_highlightedNodeColor_Button.qColor)
        if color is None or color.name() == "#000000":
            return
        self.globalGraph_highlightedNodeColor_Button.qColor = color
        self.globalGraph_highlightedNodeColor_Button.setStyleSheet('QPushButton{background:' + color.name() + ';}')

    @staticmethod
    def openConfigView():
        if ConfigView.configView is None:
            ConfigView.configView = ConfigView()
        else:
            ConfigView.configView.showNormal()
            ConfigView.configView.activateWindow()

    def closeEvent(self, event):
        saveGeom(self, "AnkiNoteLinkerConfig")
        ConfigView.configView = None
        event.accept()


mw.addonManager.setConfigAction(__name__, ConfigView.openConfigView)
