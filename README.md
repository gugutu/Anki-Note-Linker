## Link Anki notes to build knowledge network

[View on AnkiWeb](https://ankiweb.net/shared/info/1077002392)

![show.gif](show.gif)

You can easily connect your Anki notes together by this add-on, forming a web of interconnected information. 
By establishing links between relevant notes, you can create a comprehensive and organized knowledge base that reflects the relationships between various concepts, ideas, and topics.

### Usage

#### In the editor:

`Alt+k` generates a new link

`Alt+j` create link template

`Double click` link to open the corresponding note in a new window

#### In the link page:

`Left click` to open the corresponding note in the current window

`Right click` to open the corresponding note in a new window

`Middle click` to open the corresponding note in the browser

#### Right-click menu:

- Copy note ID

- Copy note link

- Open note in new window

### Link Format

`[Link Title|nidxxxxxxxxxxxxx]`

The link title is the content displayed in the card. If the title contains`[`, it needs to be escaped with`\[`

`x` is the ID of the note, consisting of 13 digits

---
### How to display notes properly without this add-on (like AnkiDroid)

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
### Roadmap

- Performance optimization

- Global relationship diagram

---
The following projects were used in this project:

- [Force graph](https://github.com/vasturiano/force-graph)

- [d3](https://github.com/d3/d3)

The implementation of this add-on is inspired by the following add-ons:

- [link Cards Notes and Preview them in extra window](https://ankiweb.net/shared/info/1423933177)

- [Editor Live Preview](https://ankiweb.net/shared/info/1960039667)