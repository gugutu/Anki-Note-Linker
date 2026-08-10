function getTr(s) {
    if (ankiLanguage !== 'zh-CN') {
        if (s === 'enableImagePreview') return 'Enable Image Previews';
        return s;
    }
    switch (s) {
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
        case 'Automatically show links panel when entering reviewer':
            return '进入复习界面时自动显示链接面板'
        case 'Automatically show graph panel when entering reviewer':
            return '进入复习界面时自动显示关系图面板'
        case 'Collapse cloze in links panel':
            return '折叠链接面板中的完形填空'
        case 'Show forward link title above note summary in links panel':
            return '在链接面板的正向链接摘要上方显示链接标题'
        case 'Node size scaling by link count':
            return '根据链接数量调整节点大小'
        case 'Do not scale':
            return '不根据链接数量调整'
        case 'Outgoing links only':
            return '只算连出的链接'
        case 'Total links':
            return '连入和连出的链接都算'
        case 'If the "hjp-linkmaster" add-on is installed, use its previewer':
            return '如果安装了“hjp-linkmaster”插件，则使用它的预览器'
        case 'The position of links/graph panel relative to the editor':
            return '链接/图形面板相对于编辑器的位置'
        case 'The position of links/graph panel relative to the reviewer':
            return '链接/图形面板相对于复习界面的位置'
        case 'Split ratio between editor and panels':
            return '编辑器和面板之间的显示比例'
        case 'Split ratio between links panel and graph panel':
            return '链接面板和图形面板之间的显示比例'
        case 'Split ratio between reviewer and panel':
            return '复习界面和侧边面板之间的显示比例'
        case 'Note fields displayed in the note summary':
            return '笔记摘要中显示的笔记字段'
        case 'Default search text':
            return '默认搜索文本'
        case 'Default filter text for highlighted nodes':
            return '高亮节点的默认筛选文本'
        case 'Default display of single nodes':
            return '默认显示单独的节点'
        case 'Default display of tag nodes':
            return '默认显示标签节点'
        case 'Node color':
            return '节点颜色'
        case 'Highlighted node color':
            return '高亮节点颜色'
        case 'Tag node color':
            return '标签节点颜色'
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
        case 'The note fields displayed in the note summary (content shown in the link panel or graphic). \n' +
        'The add-on will find the first matching field to display as the note summary. \n' +
        'If no field is set or there is no matching field, the first field of the note will be used by default.':
            return '在笔记摘要（链接面板或图形中显示的内容）中显示的笔记字段。\n插件将找到第一个匹配的字段将其显示为笔记摘要。\n如果没有设定或没有匹配的字段，则默认使用笔记的第一个字段。'
        case 'enableImagePreview':
        case 'Enable Image Previews':
            return '启用图片预览'
        case 'Enable Smooth Graph Zoom':
            return '启用关系图平滑缩放'
        case 'Advanced Graph Zoom Settings':
            return '高级关系图缩放设置'
        case 'Zoom-out limit':
            return '缩小限制'
        case 'Zoom-in limit':
            return '放大限制'
        case 'Normal zoom speed':
            return '普通缩放速度'
        case 'Smooth zoom speed':
            return '平滑缩放速度'
        case 'Smooth zoom step limit':
            return '平滑缩放单步限制'
        case 'Smooth zoom response range':
            return '平滑缩放响应范围'
        case 'Smooth zoom duration (ms)':
            return '平滑缩放时长（毫秒）'
        case 'Auto-fit zoom-in limit':
            return '自动适配放大限制'
        case 'Smoothly animates mouse wheel zoom. Leave off if zoom should feel immediate.':
            return '用动画平滑处理鼠标滚轮缩放。如果希望缩放立即响应，可以保持关闭。'
        case 'Controls how far you can zoom out. Smaller values show more of a large graph at once; larger values keep nodes from becoming extremely tiny. Range: 0.001-1. Default: 0.01.':
            return '控制关系图最多能缩小到什么程度。数值越小，一屏能看到的大图节点越多；数值越大，可以避免节点变得过小。范围：0.001-1。默认值：0.01。'
        case 'Controls how far you can zoom in. Larger values allow closer inspection of individual nodes. Range: 1-100. Default: 100.':
            return '控制关系图最多能放大到什么程度。数值越大，越适合近距离查看单个节点。范围：1-100。默认值：100。'
        case 'Controls how strongly the view reacts to each wheel movement when smooth zoom is off. Larger values feel faster; smaller values feel slower and more controlled. Range: 0.1-5. Default: 1.':
            return '控制未启用平滑缩放时，每次滚动滚轮对视图缩放的影响。数值越大，缩放越快；数值越小，缩放越慢、越稳。范围：0.1-5。默认值：1。'
        case 'Controls how strongly the view reacts to each wheel movement when smooth zoom is on. Larger values move the zoom target faster; smaller values make the movement gentler. Range: 0.1-5. Default: 1.':
            return '控制启用平滑缩放时，每次滚动滚轮对目标缩放的影响。数值越大，目标变化越快；数值越小，移动越柔和。范围：0.1-5。默认值：1。'
        case 'Caps how much one wheel movement can change the zoom target in smooth mode. Lower values prevent sudden jumps; higher values allow stronger zoom bursts. Range: 0.01-1. Default: 0.15.':
            return '限制平滑模式下单次滚轮动作最多能改变多少目标缩放。数值越小，越不容易突然跳变；数值越大，快速滚动时缩放力度更强。范围：0.01-1。默认值：0.15。'
        case 'Controls how far the animation target may get ahead of the current view while you keep scrolling. Lower values feel steadier; higher values feel more responsive but can overshoot more. Range: 0.05-2. Default: 0.4.':
            return '控制连续滚动时，动画目标可以比当前视图提前多少。数值越小越稳定；数值越大响应更快，但也更容易有过冲感。范围：0.05-2。默认值：0.4。'
        case 'How long each smooth zoom animation lasts. Lower values feel snappier; higher values feel softer and slower. Range: 0-1000 ms. Default: 250 ms.':
            return '控制每次平滑缩放动画持续多久。数值越小，响应越利落；数值越大，动画越柔和但也越慢。范围：0-1000 毫秒。默认值：250 毫秒。'
        case 'Caps how much the graph may automatically zoom in when fitting nodes into view. Lower values keep the initial view wider; higher values let small graphs open closer. Range: 0.1-10. Default: 1.4.':
            return '控制关系图自动适配节点到视野内时，最多允许放大到什么程度。数值越小，初始视野越宽；数值越大，小型关系图打开时会离节点更近。范围：0.1-10。默认值：1.4。'
        case 'Zoom-out limit must be smaller than zoom-in limit.':
            return '缩小限制必须小于放大限制。'
        case 'On macOS, new installs use Command + Option shortcuts to avoid conflicts with Option-based character input. Anki/Qt may display these shortcuts as Ctrl+Alt in the configuration. Existing shortcut settings are not changed.':
            return '在 macOS 上，新安装用户默认使用 Command + Option 快捷键，以避免和 Option 输入特殊字符冲突。Anki/Qt 的快捷键配置中可能会将这些快捷键显示为 Ctrl+Alt。已有快捷键设置不会被自动修改。'
        default:
            return s
    }
}
