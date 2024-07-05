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
        elif s == 'Global Relationship Graph (Experimental)':
            return '全局关系图（实验性）'
        elif s == 'The corresponding note does not exist':
            return '对应笔记不存在'
        elif s == 'Please add the current note first':
            return '请先添加当前笔记'
        elif s == "Please select a single note/card":
            return '请选中单条笔记/卡片'
        elif s == 'The content in the clipboard is not a note ID':
            return '剪贴板中的内容不是笔记ID'
        elif s == 'Current note has been deleted':
            return '当前笔记已被删除'
        elif s == 'Display single notes':
            return '显示单独的笔记'
        elif s == 'Search':
            return '搜索'
        elif s == 'Search notes:':
            return '搜索笔记：'
        elif s == 'Highlight specified notes:':
            return '高亮指定的笔记：'
        elif s == 'Config':
            return '设置'
        elif s == 'Basic':
            return '基础'
        elif s == 'Global Relationship Graph':
            return '全局关系图'
        elif s == 'Shortcut keys':
            return '快捷键'
        elif s == 'Anki-Note-Linker Config':
            return 'Anki-Note-Linker 设置'
        elif s == 'left':
            return '左'
        elif s == 'right':
            return '右'
        elif s == 'Automatically show links panel when entering editor':
            return '进入编辑器时自动显示链接面板'
        elif s == 'Automatically show graph panel when entering editor':
            return '进入编辑器时自动显示关系图面板'
        elif s == 'Collapse cloze in links panel':
            return '折叠链接面板中的完形填空'
        elif s == 'Collapse cloze in links panel':
            return '折叠链接面板中的完形填空'
        elif s == 'If the "hjp-linkmaster" add-on is installed, use its previewer':
            return '如果安装了“hjp-linkmaster”插件，则使用它的预览器'
        elif s == 'The position of links/graph panel relative to the editor':
            return '链接/图形面板相对于编辑器的位置'
        elif s == 'Split ratio between editor and panels':
            return '编辑器和面板之间的显示比例'
        elif s == 'Split ratio between links panel and graph panel':
            return '链接面板和图形面板之间的显示比例'
        elif s == 'Default search text':
            return '默认搜索文本'
        elif s == 'Default filter text for highlighted nodes':
            return '高亮节点的默认筛选文本'
        elif s == 'Default display of single nodes':
            return '默认显示单独的节点'
        elif s == 'Node color':
            return '节点颜色'
        elif s == 'Highlighted node color':
            return '高亮节点颜色'
        elif s == 'Graph background color':
            return '图背景颜色'
        elif s == 'Restore Defaults':
            return '恢复默认值'
        elif s == 'Cancel':
            return '取消'
        elif s == 'OK':
            return '确认'
        elif s == 'The format of "split ratio" is incorrect':
            return '“显示比例”的格式不正确'
        elif s == 'Max displayed lines per link in links panel':
            return '链接面板中每个链接的最大显示行数'
        elif s == 'For better performance, select a display driver other than "Software" to enable the new renderer. The old renderer is no longer maintained.':
            return '为了获得更好的性能，请在Anki设置中选择除"Software"之外的显示驱动以启用新的渲染器，旧的渲染器将不再维护。'
        else:
            return s
