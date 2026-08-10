const SOUND_MARKUP = /\[sound:.*?\]/g;

export function htmlToPlainText(html: string): string {
  const documentNode = new DOMParser().parseFromString(html.replace(SOUND_MARKUP, " "), "text/html");
  for (const breakElement of documentNode.querySelectorAll("br")) {
    breakElement.replaceWith(" ");
  }
  const visibleText = documentNode.body.innerText || documentNode.body.textContent || "";
  const text = visibleText.replace(/\n+/g, " ").trim();
  if (text !== "") {
    return text;
  }
  const fallback = documentNode.body.innerHTML.replace(/(<br\s*\/?>|\n)+/g, " ").trim();
  return fallback === "" ? "\n" : fallback;
}
