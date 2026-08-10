import { expect, it } from "vitest";

import { htmlToPlainText } from "../../src/links/content";

it("converts rich note summaries to plain text", () => {
  expect(htmlToPlainText("<b>Hello</b><br>world [sound:test.mp3]")).toBe("Hello world");
});

it("returns a stable placeholder for empty summaries", () => {
  expect(htmlToPlainText("<br>\n")).toBe("\n");
});
