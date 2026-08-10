import { processNoteContent } from "./content";
import type { GraphNode } from "./types";

export function prepareNodeContent(
  node: GraphNode,
  imagePreviewEnabled: boolean,
  mediaServerUrl: string,
  invalidNoteText: string,
): void {
  delete node.imageSrc;
  if (node.mainField === null) {
    node.renderText = invalidNoteText;
    node.type = "invalid";
    return;
  }
  if (!node.mainField.includes("<") && !node.mainField.includes("&lt;")) {
    node.renderText = node.mainField;
    return;
  }

  const processed = processNoteContent(node.mainField, imagePreviewEnabled, mediaServerUrl);
  const text = processed.text.trim();
  if (processed.imageSrc !== undefined) {
    node.imageSrc = processed.imageSrc;
  }
  if (processed.imageSrc !== undefined && text !== "") {
    node.renderText = `${text} (+img)`;
  } else if (processed.imageSrc !== undefined) {
    node.renderText = "[Image]";
  } else {
    node.renderText = text || "\n";
  }
}
