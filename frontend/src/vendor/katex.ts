import katex from "katex";
import renderMathInElement from "katex/contrib/auto-render";
import "katex/contrib/mhchem";

Object.assign(globalThis, { katex, renderMathInElement });
