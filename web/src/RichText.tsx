import katex from "katex";
import { memo } from "react";
import notation from "./notation.json";
import { mathTokens, mathBody, isMath } from "./math";
import "katex/dist/katex.min.css";
const formulaCache = new Map<string, string>();
function renderFormula(text: string) {
  const cached = formulaCache.get(text);
  if (cached !== undefined) return cached;
  const rendered = katex.renderToString(mathBody(text), {
    throwOnError: false,
    trust: false,
    strict: "ignore",
    displayMode: text.startsWith("$$") || text.startsWith("\\["),
    maxExpand: 1000,
    maxSize: 20,
  });
  if (formulaCache.size >= 512)
    formulaCache.delete(formulaCache.keys().next().value!);
  formulaCache.set(text, rendered);
  return rendered;
}
export const RichText = memo(function RichText({ text }: { text: string }) {
  const mappings: Record<string, string> = notation;
  text = Object.hasOwn(mappings, text) ? mappings[text] : text;
  return (
    <>
      {mathTokens(text).map((s, i) =>
        isMath(s) ? (
          <span
            key={i}
            className={
              s.startsWith("$$") || s.startsWith("\\[")
                ? "math-display"
                : "math-inline"
            }
            dangerouslySetInnerHTML={{
              __html: renderFormula(s),
            }}
          />
        ) : (
          <span key={i}>{s}</span>
        ),
      )}
    </>
  );
});
