/** Stable, bounded verbatim excerpts. Models select IDs instead of retyping quotations. */
export function excerpts(passage: string) {
  const words = passage.trim().split(/\s+/);
  const result: { anchor: string; quote: string }[] = [];
  for (let i = 0; i < words.length; i += 22) {
    const quote = words.slice(i, i + 22).join(" ");
    if (quote.length >= 12 && quote.length <= 500)
      result.push({ anchor: `p${i / 22 + 1}`, quote });
  }
  return result;
}
