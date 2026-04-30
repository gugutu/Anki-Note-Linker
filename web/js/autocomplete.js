// this was a pain in the ass to get working :)

(function () {
    // prevent multiple initializations
    if (window.AnkiNoteLinkerLoaded) return;
    window.AnkiNoteLinkerLoaded = true;

    // state management
    let keyBuffer = "";
    let menu = null;
    let searchResults = [];
    let isMenuVisible = false;
    let selectedIndex = -1;
    let currentQuery = "";

    //communicate with anki backend
    const sendToPython = (message) => {
        try {
            if (typeof pycmd !== 'undefined') {
                pycmd(message);
            } else if (window.qt && window.qt.postMessage) {
                window.qt.postMessage(message, () => { });
            }
        } catch (error) {
            console.error("AnkiNoteLinker: Communication error", error);
        }
    };

    // ui
    const MENU_STYLE = `
        position: fixed; 
        background: #1e1e1e; 
        color: #ffffff; 
        border: 1px solid #3e6ec5; 
        border-radius: 8px; 
        z-index: 2147483647; 
        width: 320px; 
        max-height: 250px; 
        overflow-y: auto; 
        display: none; 
        font-family: -apple-system, system-ui, sans-serif; 
        font-size: 13px; 
        padding: 4px 0; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    `;

    const createMenuElement = () => {
        if (menu) return;
        menu = document.createElement('div');
        menu.id = "anki-note-linker-menu";
        menu.style.cssText = MENU_STYLE;
        document.body.appendChild(menu);
    };

    // Callback triggered by Python when search results arrive
    window.onAnkiNoteLinkerSearchResults = (data) => {
        searchResults = data || [];
        if (!isMenuVisible) return;

        if (searchResults.length > 0) {
            updateMenuUI();
        } else {
            hideAutocompleteMenu();
        }
    };

    // Renders suggestion list and handles positioning
    const updateMenuUI = () => {
        createMenuElement();
        menu.style.display = 'block';
        menu.innerHTML = '';

        if (selectedIndex === -1) selectedIndex = 0;

        // Position menu near the current cursor
        const selection = window.getSelection();
        let wasPositioned = false;

        if (selection.rangeCount > 0) {
            const rect = selection.getRangeAt(0).getBoundingClientRect();
            if (rect.top !== 0 || rect.left !== 0) {
                menu.style.left = `${rect.left}px`;
                menu.style.top = `${rect.bottom + 8}px`;
                wasPositioned = true;
            }
        }

        // Fallback: center menu if cursor position is unavailable
        if (!wasPositioned) {
            menu.style.left = '50%';
            menu.style.top = '100px';
            menu.style.transform = 'translateX(-50%)';
        } else {
            menu.style.transform = 'none';
        }

        // Populate results
        searchResults.forEach((note, index) => {
            const item = document.createElement('div');
            item.style.padding = '8px 12px';
            item.style.cursor = 'pointer';
            item.style.borderBottom = '1px solid #2a2a2a';
            item.style.backgroundColor = (index === selectedIndex) ? '#2d4a85' : 'transparent';
            item.textContent = note.label;

            // Handle click selection
            item.onmousedown = (event) => {
                event.preventDefault();
                finalizeSelection(note.label, note.id);
            };

            menu.appendChild(item);
        });
    };

    // Insert link and replace trigger text
    const finalizeSelection = (label, noteId) => {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;

        // Highlight backwards to capture the '[' and search query
        const charsToReplace = keyBuffer.length;
        for (let i = 0; i < charsToReplace; i++) {
            selection.modify("extend", "backward", "character");
        }

        // Replace highlighted text with formatted link
        const linkText = `[${label}|nid${noteId}]`;
        document.execCommand('insertText', false, linkText);

        hideAutocompleteMenu();
    };

    const hideAutocompleteMenu = () => {
        if (menu) menu.style.display = 'none';
        isMenuVisible = false;
        currentQuery = "";
        selectedIndex = -1;
        keyBuffer = "";
    };

    // Main keyboard event handler
    const onKeyDown = (event) => {
        // Navigation within the menu
        if (isMenuVisible && searchResults.length > 0) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, searchResults.length - 1);
                updateMenuUI();
                return;
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateMenuUI();
                return;
            } else if (event.key === 'Enter' && selectedIndex !== -1) {
                event.preventDefault();
                finalizeSelection(searchResults[selectedIndex].label, searchResults[selectedIndex].id);
                return;
            }
        }

        // Track characters for the search trigger
        if (event.key === '[') {
            keyBuffer += '[';
        } else if (event.key === 'Backspace') {
            if (keyBuffer.length > 0) {
                keyBuffer = keyBuffer.slice(0, -1);
            }
            if (keyBuffer.lastIndexOf('[') === -1) {
                hideAutocompleteMenu();
            }
        } else if (event.key && event.key.length === 1) {
            keyBuffer += event.key;
        } else if (event.key === 'Enter' || event.key === 'Escape') {
            keyBuffer = "";
            hideAutocompleteMenu();
            return;
        }

        // Identify search trigger
        const triggerIndex = keyBuffer.lastIndexOf('[');
        if (triggerIndex !== -1) {
            isMenuVisible = true;
            const newQuery = keyBuffer.substring(triggerIndex + 1);

            if (newQuery !== currentQuery) {
                currentQuery = newQuery;
                sendToPython(`AnkiNoteLinker-searchNotes:${currentQuery}`);
            }
        } else {
            if (!isMenuVisible && menu) menu.style.display = 'none';
        }
    };

    // Global event listeners
    window.addEventListener('keydown', onKeyDown, true);

    // Close menu when clicking outside
    window.addEventListener('mousedown', (event) => {
        const isMenuClick = event.target?.id?.includes('anki-note-linker');
        if (isMenuClick) return;

        keyBuffer = "";
        hideAutocompleteMenu();
    }, true);

})();
