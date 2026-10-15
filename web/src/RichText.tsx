import katex from "katex";
import notation from "./notation.json";
import { mathTokens, mathBody, isMath } from "./math";
import "katex/dist/katex.min.css";
export function RichText({ text }: { text: string }) {
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
              __html: katex.renderToString(mathBody(s), {
                throwOnError: false,
                trust: false,
                strict: "warn",
                displayMode: s.startsWith("$$") || s.startsWith("\\["),
                maxExpand: 1000,
                maxSize: 20,
              }),
            }}
          />
        ) : (
          <span key={i}>{s}</span>
        ),
      )}
    </>
  );
}
