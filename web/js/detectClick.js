window.addEventListener('dblclick', function (e) {
    var nidreg = /^nid\d{13}$/;
    var newreg = /^new\d{8}$/;
    const st = window.getSelection().toString();
    if (st !== '') {
        if (nidreg.test(st)) {
            const nid = st.slice(3)
            pycmd('AnkiNoteLinker-openNoteInNewEditor' + nid);
        } else if (newreg.test(st)) {
            const placeholder = st.slice(3)
            pycmd('AnkiNoteLinker-openAddNoteWindow' + placeholder)
        }
    }
});