function getTr(s) {
    if (ankiLanguage !== 'zh-CN') return s;
    else switch (s) {
        case 'Back Links':
            return '反向链接'
        case 'Forward Links':
            return '正向链接'
        case 'None':
            return '无'
        case 'Invalid note':
            return '无效笔记'
        case 'Invalid link':
            return '无效链接'
        case 'Basic':
            return '基础'
        case 'Global Relationship Graph':
            return '全局关系图'
        case 'Shortcut keys':
            return '快捷键'
        case 'left':
            return '左'
        case 'right':
            return '右'
        case 'Automatically show links panel when entering editor':
            return '进入编辑器时自动显示链接面板'
        case 'Automatically show graph panel when entering editor':
            return '进入编辑器时自动显示关系图面板'
        case 'Collapse cloze in links panel':
            return '折叠链接面板中的完形填空'
        case 'If the "hjp-linkmaster" add-on is installed, use its previewer':
            return '如果安装了“hjp-linkmaster”插件，则使用它的预览器'
        case 'The position of links/graph panel relative to the editor':
            return '链接/图形面板相对于编辑器的位置'
        case 'Split ratio between editor and panels':
            return '编辑器和面板之间的显示比例'
        case 'Split ratio between links panel and graph panel':
            return '链接面板和图形面板之间的显示比例'
        case 'Default search text':
            return '默认搜索文本'
        case 'Default filter text for highlighted nodes':
            return '高亮节点的默认筛选文本'
        case 'Default display of single nodes':
            return '默认显示单独的节点'
        case 'Node color':
            return '节点颜色'
        case 'Highlighted node color':
            return '高亮节点颜色'
        case 'Graph background color':
            return '图背景颜色'
        case 'Restore Defaults':
            return '恢复默认值'
        case 'Cancel':
            return '取消'
        case 'OK':
            return '确认'
        case 'The format of "split ratio" is incorrect':
            return '“显示比例”的格式不正确'
        case 'Max displayed lines per link in links panel':
            return '链接面板中每个链接的最大显示行数'
        case 'Copy current note ID':
            return '复制当前笔记ID'
        case 'Copy current note link':
            return '复制当前笔记链接'
        case 'Open current note in new window':
            return '在新窗口中打开当前笔记'
        case 'Insert link with copied note ID':
            return '插入带有已复制的笔记ID的链接'
        case 'Insert new link':
            return '插入新链接'
        case 'Insert link template':
            return '插入链接模版'
        default:
            return s
    }
}