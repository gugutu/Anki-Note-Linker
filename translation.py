import anki

lang = anki.lang.current_lang


def getTr(s: str) -> str:
    if lang != 'zh-CN':
        return s
    else:
        if s == 'Copy note ID':
            return '复制笔记ID'
        elif s == 'Copy note link':
            return '复制笔记链接'
        elif s == 'Open note in new window':
            return '在新窗口中打开笔记'
        elif s == 'Insert link with copied note ID':
            return '插入带有剪贴板中笔记ID的链接'
        elif s == 'Insert new link':
            return '插入新链接'
        elif s == 'Insert link template':
            return '插入链接模版'
        elif s == 'Copied note ID':
            return '已复制笔记ID'
        elif s == 'Copied note link':
            return '已复制笔记链接'
        elif s == 'Toggle Links Page':
            return '显示/隐藏链接页面'
        elif s == 'Toggle Graph Page':
            return '显示/隐藏关系图'
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
        else:
            return s
