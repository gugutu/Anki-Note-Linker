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

You can customize the style of the links by using the CSS selector: `.noteLink`

## Usage

### In the editor:

#### Copy note ID

Copy the ID of the current note in the editor by using the right-click menu or pressing `Alt+Shift+C`

#### Copy note link

Copy the link of the current note in the editor by using the right-click menu or pressing `Alt+Shift+L`

#### Insert link with copied note ID

Generate a link from the note ID in the clipboard and the currently selected text by either using the right-click menu or pressing `Alt+Shift+V`

#### Insert new link

Generate a new link from the currently selected text by either using the right-click menu or pressing `Alt+Shift+N`

Double-clicking the generated link allows adding a corresponding new note

#### Insert link template

Generate a link template from the currently selected text by either using the right-click menu or pressing `Alt+Shift+T`

The generated link template looks like this: `[selected text|nid]`, you need to manually complete it

_Note: If no text is selected, using the above actions will generate a link without a title_

#### Open current note in new window

Open current note in new window by using the right-click menu or pressing `Alt+Shift+W`

#### Open the note corresponding to the link

`Double click link` to open the corresponding note in a new window

### In the links panel / graph panel:

`Left click link` to open the corresponding note in the current window

`Right click link` to open the corresponding note in a new window

`Middle click link` to open the corresponding note in the browser (unsupported in graph view)

### In the previewer / reviewer / global graph:

`Left click link` to open the corresponding note in an editor window

`Right click link` to open the corresponding note in a previewer window

### Global relationship graph (Experimental)

Entrance: `Menu -> Anki Note Linker -> Global Relationship Graph (Experimental)`

Please set the video driver in Anki preference to an option other than `Software`, as it can significantly decrease graphic performance

### Customize shortcut keys

You can customize the shortcut keys according to your preferences in add-on configuration

If there is no response when using the shortcut key, it may be due to a shortcut key conflict. Please try changing the shortcut key

---
## How to display note links properly without this add-on (such as on AnkiDroid, AnkiWeb, or AnkiMobile clients)

This add-on automatically renders note links as corresponding content on the desktop version of Anki. Without the add-on, the links will not be rendered properly, affecting use on mobile devices. However, you can still regain some functionality.

If you have already generated note links and need to use them without the add-on, you can follow the steps below to get links working:

1. In the card template, add a `class` attribute `"linkRender"` to each note field on the front and back sides. You can also customize the attribute's name.

```html
<div class="linkRender">{{Front}}</div>
<div class="linkRender">{{Back}}</div>
<!-- If the field already has a class attribute, 
you can use a space to separate the new attribute from the original one -->
<div class="otherClassName linkRender">{{Addition}}</div>
```
2. Copy the following code to the end of the card template on both sides. Rename the `linkRender` attribute in the code if you changed it. Set the `disableLinks` variable to `true` if you only want the text to render (removes the "[nid|]" marker).

```html
<script>
    var disableLinks = false; // Change to true if you want to disable all link rendering for clients without add-on
    if (!window.AnkiNoteLinkerIsActive) {
        const renderLinks = _ => {
            document.querySelectorAll('.linkRender').forEach(element => { // You can rename "linkRender" on this line, but leave the "." in front
                element.innerHTML = element.innerHTML.replace(
                    /\[((?:[^\[]|\\\[)*)\|nid(\d{13})\]/g,
                    (match, title, nid) => {
                        title = title.replace(/\\\[/g, '[');
                        let link;
                        if (document.documentElement.classList.contains('iphone') || document.documentElement.classList.contains('ipad')) {
                            link = `anki://x-callback-url/search?query=nid%3a${nid}`;
                        } else try {
                            window.jsAPI ||= new AnkiDroidJS({ version: "0.0.3", developer: "github.com/gugutu" });
                            link = `javascript:window.jsAPI.ankiSearchCard('nid:${nid}')`;
                        } catch (e) {
                            link = `https://ankiuser.net/edit/${nid}" target="_blank`;
                        }
                        return disableLinks ? `${title}` : `<a href="${link}" class="noteLink">${title}</a>`;
                    }
                );
            });
        };
        document.readyState !== 'loading' ? renderLinks() : document.addEventListener('DOMContentLoaded', renderLinks, { once: true });
    }
</script>
```

3. Save the card template and sync your deck to AnkiWeb.

After completing these operations, Anki will automatically display the correct content.

If you click a link on an AnkiDroid or AnkiMobile client, it will attempt to display the corresponding note's flashcard in the card browser; if you click a link on AnkiWeb, it will open the AnkiWeb edit page for the corresponding note. If you changed the `disableLinks` variable to `true`, then the original content of the card will be displayed without any links.

---
This add-on is inspired by [Obsidian](https://obsidian.md/)

The following projects were used in this project:

- [pixijs](https://github.com/pixijs/pixijs)

- [d3](https://github.com/d3/d3)

- [KaTeX](https://github.com/KaTeX/KaTeX)

- [Force graph](https://github.com/vasturiano/force-graph)

The implementation of this add-on is inspired by the following add-ons:

- [link Cards Notes and Preview them in extra window](https://ankiweb.net/shared/info/1423933177)

- [hjp-linkmaster](https://ankiweb.net/shared/info/1420819673)

- [Editor Live Preview](https://ankiweb.net/shared/info/1960039667)

---
Add-on code：1077002392