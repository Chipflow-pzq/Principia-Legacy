import assert from "node:assert/strict";
import { test } from "node:test";
import katex from "katex";
import { mathTokens, isMath, mathBody } from "../src/math.ts";

test("currency and escaped dollar signs do not consume neighboring equations", () => {
  const text = String.raw`At $5 the firm sells units at $3.09, giving $(5-3.09)\times85\approx\$162.35$. Revenue is \$90 at \$9 per shirt.`;
  const formulas = mathTokens(text).filter(isMath);
  assert.deepEqual(formulas, [String.raw`$(5-3.09)\times85\approx\$162.35$`]);
  assert.doesNotThrow(() =>
    katex.renderToString(mathBody(formulas[0]), { throwOnError: true }),
  );
});

test("inline, display, numeric and legacy notation stay readable", () => {
  const text = String.raw`$5 + 1$; $1,000$; $1/0.10 = 10$; $$x^2$$; \(a+b\); \[c^2\]; sqrt(x)`;
  assert.equal(mathTokens(text).filter(isMath).length, 7);
  assert.equal(isMath("$5 per shirt"), false);
  assert.equal(isMath("$unclosed"), false);
  assert.equal(isMath(String.raw`\$90`), false);
});
