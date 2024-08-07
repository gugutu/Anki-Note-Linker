import anki

lang = anki.lang.current_lang


def getTr(s: str) -> str:
    if lang != 'zh-CN':
        return s
    else:
        if s == 'Copy current note ID':
            return '复制当前笔记ID'
        elif s == 'Copy current note link':
            return '复制当前笔记链接'
        elif s == 'Open current note in new window':
            return '在新窗口中打开当前笔记'
        elif s == 'Insert link with copied note ID':
            return '插入带有已复制的笔记ID的链接'
        elif s == 'Insert new link':
            return '插入新链接'
        elif s == 'Insert link template':
            return '插入链接模版'
        elif s == 'Copied note ID':
            return '已复制笔记ID'
        elif s == 'Copied note link':
            return '已复制笔记链接'
        elif s == 'Toggle Links Panel':
            return '显示/隐藏链接面板'
        elif s == 'Toggle Graph Panel':
            return '显示/隐藏关系图面板'
        elif s == 'Show Links Panel':
            return '显示链接面板'
        elif s == 'Global Relationship Graph':
            return '全局关系图'
        elif s == 'Display tag nodes':
            return '显示标签节点'
        elif s == 'The corresponding note does not exist':
            return '对应笔记不存在'
        elif s == 'Please add the current note first':
            return '请先添加当前笔记'
        elif s == "Please select a single note/card":
            return '请选中单条笔记/卡片'
        elif s == 'The content in the clipboard is not a note ID':
            return '剪贴板中的内容不是笔记ID'
        elif s == 'Display single nodes':
            return '显示单独的节点'
        elif s == 'Search':
            return '搜索'
        elif s == 'Search notes:':
            return '搜索笔记：'
        elif s == 'Highlight specified notes:':
            return '高亮指定的笔记：'
        elif s == 'Config':
            return '设置'
        elif s == 'Anki-Note-Linker Config':
            return 'Anki-Note-Linker 设置'
        elif s == 'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.':
            return '为了获得更好的性能，请在Anki设置中选择除"Software"之外的显示驱动以启用新的渲染器，旧的渲染器将不再维护。'
        else:
            return s
