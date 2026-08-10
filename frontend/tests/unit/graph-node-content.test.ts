import { describe, expect, it } from "vitest";

import { prepareNodeContent } from "../../src/graph/node-content";
import type { GraphNode } from "../../src/graph/types";

describe("graph node content", () => {
  it("clears a stale image when the replacement field is plain text", () => {
    const node: GraphNode = {
      id: 1,
      imageSrc: "http://127.0.0.1/old.png",
      mainField: "updated",
      type: "normal",
    };

    prepareNodeContent(node, true, "http://127.0.0.1/", "Invalid note");

    expect(node.imageSrc).toBeUndefined();
    expect(node.renderText).toBe("updated");
  });

  it("marks missing notes without attempting HTML processing", () => {
    const node: GraphNode = { id: 1, mainField: null, type: "normal" };

    prepareNodeContent(node, true, "http://127.0.0.1/", "Invalid note");

    expect(node.type).toBe("invalid");
    expect(node.renderText).toBe("Invalid note");
  });
});
