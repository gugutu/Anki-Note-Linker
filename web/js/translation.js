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
        default:
            return s
    }
}