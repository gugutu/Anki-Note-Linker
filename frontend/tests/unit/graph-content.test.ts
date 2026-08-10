import { describe, expect, it } from "vitest";

import { preserveNodePosition, processNoteContent, updateNodeContent } from "../../src/graph/content";
import type { GraphNode } from "../../src/graph/types";

describe("processNoteContent", () => {
  it("extracts a relative image and removes markup from the label", () => {
    const result = processNoteContent(
      '<div>Hello <img src="collection.media/image.png">[sound:test.mp3]</div>',
      true,
      "http://127.0.0.1:1234/",
    );

    expect(result).toEqual({
      imageSrc: "http://127.0.0.1:1234/collection.media/image.png",
      text: "Hello",
    });
  });

  it("does not expose an image when previews are disabled", () => {
    expect(processNoteContent('<img src="image.png">Text', false, "http://localhost/")).toEqual({ text: "Text" });
  });

  it("removes a stale image when refreshed content no longer has one", () => {
    const node: GraphNode = {
      id: 1234567890123,
      imageSrc: "http://localhost/old.png",
      mainField: "Plain text",
      type: "normal",
    };

    updateNodeContent(node, true, "http://localhost/");

    expect(node.imageSrc).toBeUndefined();
    expect(node.renderText).toBe("Plain text");
  });
});

describe("preserveNodePosition", () => {
  it("copies only simulation position from an old node", () => {
    const next: GraphNode = { id: 1, mainField: "new", type: "normal" };
    const previous: GraphNode = {
      id: 1,
      imageSrc: "old.png",
      mainField: "old",
      type: "normal",
      vx: 1,
      x: 10,
      y: 20,
    };

    preserveNodePosition(next, previous);

    expect(next).toEqual({ id: 1, mainField: "new", type: "normal", vx: 1, x: 10, y: 20 });
  });
});
