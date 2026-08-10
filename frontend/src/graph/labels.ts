import type { GraphNode } from "./types";

export interface GraphTextElement extends HTMLDivElement {
  addedBefore: boolean;
  fontSize: number;
  inDocument: boolean;
  layoutLeft: number;
  layoutTop: number;
  layoutWidth: number;
  lineHeight: number;
}

export function createNodeText(node: GraphNode): GraphTextElement {
  const element = document.createElement("div") as GraphTextElement;
  element.classList.add("circleText");
  element.textContent = node.renderText ?? "";
  element.addedBefore = false;
  element.fontSize = 0;
  element.inDocument = false;
  element.layoutLeft = 0;
  element.layoutTop = 0;
  element.layoutWidth = 0;
  element.lineHeight = 0;
  return element;
}

export function createNodeLabel(node: GraphNode): HTMLDivElement {
  const label = document.createElement("div");
  label.classList.add("label");
  if (node.imageSrc !== undefined) {
    const image = document.createElement("img");
    image.src = node.imageSrc;
    image.alt = "";
    image.style.setProperty("max-width", "400px", "important");
    image.style.setProperty("max-height", "300px", "important");
    image.style.setProperty("width", "auto", "important");
    image.style.setProperty("height", "auto", "important");
    image.style.setProperty("object-fit", "contain", "important");
    image.style.display = "block";
    image.style.marginBottom = "8px";
    image.style.borderRadius = "4px";
    image.addEventListener("error", () => image.remove(), { once: true });
    label.appendChild(image);
  }
  const text = document.createElement("span");
  text.textContent = node.renderText ?? "";
  label.appendChild(text);
  return label;
}

export function positionLabel(label: HTMLDivElement, pointerX: number, pointerY: number): void {
  const maxLeft = Math.max(1, window.innerWidth - label.offsetWidth - 1);
  const left = Math.max(1, Math.min(maxLeft, pointerX - label.offsetWidth / 2));
  let top = pointerY + 25;
  if (top + label.offsetHeight > window.innerHeight) {
    top = pointerY - label.offsetHeight - 15;
  }
  label.style.left = `${String(left)}px`;
  label.style.top = `${String(top)}px`;
}

export function renderGraphMath(): void {
  try {
    renderMathInElement(document.body, {
      delimiters: [
        { display: false, left: "\\(", right: "\\)" },
        { display: true, left: "\\[", right: "\\]" },
      ],
      throwOnError: false,
    });
  } catch (error) {
    console.error("Failed to render graph math labels.", error);
  }
}
