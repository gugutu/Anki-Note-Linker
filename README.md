**English | [简体中文](README-zh.md)**

# Anki Note Linker

[View on AnkiWeb](https://ankiweb.net/shared/info/1077002392)

![show0.jpg](show0.jpg)

![show.jpg](show.jpg)

![show.gif](show.gif)

You can easily connect your Anki notes together by this add-on, forming a web of interconnected information. 
By establishing links between relevant notes, you can create a comprehensive and organized knowledge base that reflects the relationships between various concepts, ideas, and topics.

## Link Format

`[Link Title|nidxxxxxxxxxxxxx]`

The link title is the content displayed in the card. If the title contains`[`, it needs to be escaped with`\[`

`x` is the ID of the note, consisting of 13 digits

## Usage

### In the editor:

#### Copy note ID

Copy the ID of the current note in the editor by using the right-click menu or pressing `Alt+Shift+C`

#### Copy note link

Copy the link of the current note in the editor by using the right-click menu or pressing `Alt+Shift+L`

#### Insert link with copied note ID

Generate a link from the note ID in the clipboard and the currently selected text by either using the right-click menu or pressing `Alt+Shift+V`

>The `Alt+l` shortcut key in the old version is still available for use, but it will be removed in future versions. You can customize the shortcut keys in the add-on configuration.

#### Insert new link

Generate a new link from the currently selected text by either using the right-click menu or pressing `Alt+Shift+N`

Double-clicking the generated link allows adding a corresponding new note

>The `Alt+k` shortcut key in the old version is still available for use, but it will be removed in future versions. You can customize the shortcut keys in the add-on configuration.

#### Insert link template

Generate a link template from the currently selected text by either using the right-click menu or pressing `Alt+Shift+T`

The generated link template looks like this: `[selected text|nid]`, you need to manually complete it

>The `Alt+j` shortcut key in the old version is still available for use, but it will be removed in future versions. You can customize the shortcut keys in the add-on configuration.

_Note: If no text is selected, using the above actions will generate a link without a title_

#### Open current note in new window

Open current note in new window by using the right-click menu or pressing `Alt+Shift+W`

#### Open the note corresponding to the link

`Double click` link to open the corresponding note in a new window

### In the link panel / graph panel:

`Left click` to open the corresponding note in the current window

`Right click` to open the corresponding note in a new window

`Middle click` to open the corresponding note in the browser (unsupported in graph view)

### In the previewer / reviewer / global graph:

`Left click` to open the corresponding note in an editor window

`Right click` to open the corresponding note in a previewer window

### Global relationship graph (Experimental)

Entrance: `Menu -> Anki Note Linker -> Global Relationship Graph (Experimental)`

Please set the video driver in Anki preference to an option other than `Software`, as it can significantly decrease graphic performance

### Customize shortcuts

You can customize the shortcut keys according to your preferences in add-on configuration

If there is no response when using the shortcut key, it may be due to a shortcut key conflict. Please try changing the shortcut key

---
## How to display notes properly without this add-on (like AnkiDroid)

This add-on automatically renders note links as corresponding content. However, without the add-on, the links will not be rendered, such as in AnkiDroid.

If you have generated note links and need to use them without the add-on, you can add the following code to your card template. It will automatically render the correct note content even without this add-on.

```html
<script>
    requestIdleCallback(() => {
        try { AnkiNoteLinkerIsActive } catch (e) {
            document.documentElement.innerHTML = document.documentElement.innerHTML
                .replace(/\[((?:[^\[]|\\\[)*?)\|nid\d{13}\]/g, (match, title) => title.replace(/\\\[/g, '['))
        }
    })
</script>
```

---
This add-on is inspired by [Obsidian](https://obsidian.md/)

The following projects were used in this project:

- [Force graph](https://github.com/vasturiano/force-graph)

- [d3](https://github.com/d3/d3)

The implementation of this add-on is inspired by the following add-ons:

- [link Cards Notes and Preview them in extra window](https://ankiweb.net/shared/info/1423933177)

- [hjp-linkmaster](https://ankiweb.net/shared/info/1420819673)

- [Editor Live Preview](https://ankiweb.net/shared/info/1960039667)

---
Add-on code：1077002392