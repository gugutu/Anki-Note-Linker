export function requireElement<T extends HTMLElement>(id: string, constructor: new () => T): T {
  const element = document.getElementById(id);
  if (!(element instanceof constructor)) {
    throw new Error(`Expected #${id} to be a ${constructor.name}`);
  }
  return element;
}

export function requireByClass<T extends HTMLElement>(className: string, constructor: new () => T): T {
  const element = document.getElementsByClassName(className)[0];
  if (!(element instanceof constructor)) {
    throw new Error(`Expected .${className} to be a ${constructor.name}`);
  }
  return element;
}

export function setTranslatedText(id: string, message: string): void {
  requireElement(id, HTMLElement).textContent = getTr(message);
}

export function setTranslatedLabel(className: string, message: string): void {
  requireByClass(className, HTMLElement).textContent = `${getTr(message)}:`;
}
