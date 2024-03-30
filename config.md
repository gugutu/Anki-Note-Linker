### Config

`showLinksPageAutomatically` `[boolean (true | false)]`:

- Defines if the link page should show up automatically as you enter the Editor (default: `true`)

`showGraphPageAutomatically` `[boolean (true | false)]`:

- Defines if the graph page should show up automatically as you enter the Editor (default: `true`)

`splitRatio` `[string (int:int)]`:

- Defines the default split ratio of the editor view and links page (default: `"2:1"`)

`splitRatioBetweenLinksPageAndGraphPage` `[string (int:int)]`:

- Defines the default split ratio of the links page and graph page (default: `"1:1"`)

`location` `[string (left | right)]`:

- Defines which side of the editor to display (default: `"right"`)

`linkMaxLines` `[int]`:

- Defines the maximum number of lines of a single link in links page (default: `5`)

`collapseClozeInLinksPage` `[boolean (true | false)]`:

- Defines whether to collapse cloze in links page (cloze will be displayed as `[...]`)(default: `true`)

`shortcuts` `{"action": "shortcut", ...}`:

- Defines shortcut keys for actions
- If there is no response when using the shortcut key, it may be due to a shortcut key conflict. Please try changing the shortcut key.

`globalGraph.defaultSearchText` `[string]`:

- Default search text when entering the global graph (default: `"deck:current"`)

`globalGraph.defaultHighlightFilter` `[string]`:

- Default highlight filter text when entering the global graph (default: `"is:due"`)

`Use the previewer of hjp-linkmaster if it is installed` `[boolean (true | false)]`:

- Use the previewer of `hjp-linkmaster` if it is installed (default: `true`)
- `hjp-linkmaster` is another Anki note linking plugin that allows for direct review of cards in its previews
- https://ankiweb.net/shared/info/1420819673