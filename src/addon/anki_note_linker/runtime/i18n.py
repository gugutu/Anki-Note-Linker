"""Runtime translations for native Anki widgets."""

import anki

_ZH_CN = {
    "Anki-Note-Linker Config": "Anki-Note-Linker 设置",
    "Config": "设置",
    "Copied note ID": "已复制笔记ID",
    "Copied note link": "已复制笔记链接",
    "Copy current note ID": "复制当前笔记ID",
    "Copy current note link": "复制当前笔记链接",
    "Display single nodes": "显示单独的节点",
    "Display suspended notes": "显示已暂停笔记",
    "Display tag nodes": "显示标签节点",
    'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.': '为了获得更好的性能，请在Anki设置中选择除"Software"之外的显示驱动以启用新的渲染器，旧的渲染器将不再维护。',
    "Global Relationship Graph": "全局关系图",
    "Highlight specified notes:": "高亮指定的笔记：",
    "Insert link template": "插入链接模版",
    "Insert link with copied note ID": "插入带有已复制的笔记ID的链接",
    "Insert new link": "插入新链接",
    "Node size scaling by link count": "根据链接数量调整节点大小",
    "When this option is off, notes remain visible if at least one of their cards is not suspended.": "关闭此选项后，只要笔记仍有至少一张未暂停的卡片，它就会继续显示。",
    "Open current note in new window": "在新窗口中打开当前笔记",
    "Please add the current note first": "请先添加当前笔记",
    "Please select a single note/card": "请选中单条笔记/卡片",
    "Search": "搜索",
    "Search notes:": "搜索笔记：",
    "Show Graph Panel": "显示关系图面板",
    "Show Links Panel": "显示链接面板",
    "Show forward link title above note summary in links panel": "在链接面板的正向链接摘要上方显示链接标题",
    "The content in the clipboard is not a note ID": "剪贴板中的内容不是笔记ID",
    "The corresponding note does not exist": "对应笔记不存在",
    "Toggle Graph Panel": "显示/隐藏图形面板",
    "Toggle Links Panel": "显示/隐藏链接面板",
}


def getTr(message: str) -> str:
    """Return the current native-widget translation for a message."""
    if anki.lang.current_lang == "zh-CN":
        return _ZH_CN.get(message, message)
    return message
