/** Delimiters are authoritative; legacy recognition is deliberately narrow. */
const explicitMath =
  /(\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\])/g;
const legacyMath =
  /\b(?:1\/)?sqrt\([A-Za-z](?:_[a-z0-9]+)?\)|\b[A-Za-z]_[a-z0-9]\b|\bO\((?:[A-Za-z](?:\^[0-9]+)?|[0-9]+)\)|\b[A-Za-z]\^[0-9]+\b/g;
export function isMath(text: string) {
  return (
    text.startsWith("$") || text.startsWith("\\(") || text.startsWith("\\[")
  );
}
export function mathTokens(text: string): string[] {
  const normalized = text
    .split(explicitMath)
    .map((part) => {
      if (isMath(part)) return part;
      return part.replace(legacyMath, (value) => {
        const root = value.match(/^(1\/)?sqrt\((.+)\)$/);
        const latex = root
          ? root[1]
            ? `\\frac{1}{\\sqrt{${root[2]}}}`
            : `\\sqrt{${root[2]}}`
          : value;
        return `$${latex}$`;
      });
    })
    .join("");
  return normalized.split(explicitMath);
}
export function mathBody(text: string) {
  return text.replace(/^\$\$?|\$\$?$|^\\[([]|\\[)\]]$/g, "");
}
