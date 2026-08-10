import type { GraphNode } from "../graph/types";
import { requireElement } from "../shared/dom";
import { htmlToPlainText } from "./content";

const backLinks = requireElement("backLinks", HTMLDivElement);
const forwardLinks = requireElement("forwardLinks", HTMLDivElement);
const linkTitle = requireElement("linkTitle", HTMLDivElement);

function renderKatex(): void {
  renderMathInElement(document.body, {
    delimiters: [
      { display: false, left: "\\(", right: "\\)" },
      { display: true, left: "\\[", right: "\\]" },
    ],
    throwOnError: false,
  });
}

function setButtonWidths(selector: string, width: number): void {
  for (const element of document.querySelectorAll<HTMLElement>(selector)) {
    element.style.width = `${String(Math.max(0, width - 12))}px`;
  }
}

function adjustHeights(): void {
  let backWidth = backLinks.clientWidth;
  let forwardWidth = forwardLinks.clientWidth;
  setButtonWidths(".backLink-button", backWidth);
  setButtonWidths(".forwardLink-button", forwardWidth);

  const windowHeight = window.innerHeight;
  const backHeight = backLinks.scrollHeight;
  const forwardHeight = forwardLinks.scrollHeight;
  const titleHeight = linkTitle.scrollHeight;
  const totalHeight = backHeight + forwardHeight + titleHeight * 2;

  if (totalHeight < windowHeight) {
    backLinks.style.maxHeight = "";
    forwardLinks.style.maxHeight = "";
  } else {
    const backRatio = (backHeight + titleHeight) / windowHeight;
    const forwardRatio = (forwardHeight + titleHeight) / windowHeight;
    if (backRatio > 0.5 && forwardRatio > 0.5) {
      const height = `${String(windowHeight / 2 - titleHeight)}px`;
      backLinks.style.maxHeight = height;
      forwardLinks.style.maxHeight = height;
    } else if (backRatio > 0.5) {
      backLinks.style.maxHeight = `${String(windowHeight - forwardHeight - 2 * titleHeight)}px`;
      forwardLinks.style.maxHeight = "";
    } else if (forwardRatio > 0.5) {
      backLinks.style.maxHeight = "";
      forwardLinks.style.maxHeight = `${String(windowHeight - backHeight - 2 * titleHeight)}px`;
    }
  }

  if (backLinks.clientWidth < backWidth) {
    backWidth = backLinks.clientWidth;
    setButtonWidths(".backLink-button", backWidth);
  }
  if (forwardLinks.clientWidth < forwardWidth) {
    forwardWidth = forwardLinks.clientWidth;
    setButtonWidths(".forwardLink-button", forwardWidth);
  }
}

function hasSelection(): boolean {
  return (window.getSelection()?.toString().length ?? 0) > 0;
}

function openNode(nodeId: GraphNode["id"]): void {
  if (ankiContext === "BROWSER") {
    pycmd(`AnkiNoteLinker-openNoteInBrowser${String(nodeId)}`);
  } else if (ankiContext === "REVIEWER") {
    pycmd(`AnkiNoteLinker-openNoteInPreviewer${String(nodeId)}`);
  } else {
    pycmd(`AnkiNoteLinker-setNoteToEditor${String(nodeId)}`);
  }
}

function createButton(node: GraphNode, container: HTMLElement, isBackLink: boolean, showLinkTitle: boolean): void {
  const outer = document.createElement("div");
  outer.className = node.mainField === null ? "link-button-invalid" : "link-button";
  outer.classList.add(isBackLink ? "backLink-button" : "forwardLink-button");

  if (!isBackLink && showLinkTitle && node.linkTitle) {
    const title = document.createElement("div");
    title.className = "link-button-title";
    title.textContent = node.linkTitle;
    outer.append(title);
  }
  const summary = document.createElement("div");
  summary.className = "link-button-text";
  summary.textContent = node.mainField === null
    ? `${getTr("Invalid link")}${String(node.id)}`
    : htmlToPlainText(node.mainField);
  outer.append(summary);

  outer.addEventListener("click", (event) => {
    if (hasSelection()) {
      event.preventDefault();
      return;
    }
    openNode(node.id);
  });
  outer.addEventListener("dblclick", (event) => {
    event.preventDefault();
    openNode(node.id);
  });
  outer.addEventListener("contextmenu", (event) => {
    if (hasSelection()) {
      return;
    }
    event.preventDefault();
    pycmd(`AnkiNoteLinker-openNoteInNewEditor${String(node.id)}`);
  });
  outer.addEventListener("mousedown", (event) => {
    if (event.button === 1) {
      event.preventDefault();
      pycmd(`AnkiNoteLinker-openNoteInBrowser${String(node.id)}`);
    }
  });
  container.append(outer);
}

function reloadPage(
  parentNodes: GraphNode[] = [],
  childNodes: GraphNode[] = [],
  waitingForShowAnswer = false,
  showForwardLinkTitle = false,
): void {
  if (waitingForShowAnswer) {
    backLinks.textContent = "[...]";
    forwardLinks.textContent = "[...]";
    adjustHeights();
    return;
  }
  backLinks.textContent = parentNodes.length === 0 ? getTr("None") : "";
  forwardLinks.textContent = childNodes.length === 0 ? getTr("None") : "";
  for (const node of parentNodes) {
    createButton(node, backLinks, true, false);
  }
  for (const node of childNodes) {
    createButton(node, forwardLinks, false, showForwardLinkTitle);
  }
  renderKatex();
  adjustHeights();
}

requireElement("backTitle", HTMLHeadingElement).textContent = getTr("Back Links");
requireElement("forwardTitle", HTMLHeadingElement).textContent = getTr("Forward Links");
window.addEventListener("resize", adjustHeights);
window.addEventListener("load", adjustHeights);
window.reloadPage = reloadPage;
