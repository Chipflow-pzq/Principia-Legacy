/** Software comes from the installed assets; only atlas reading links pin content. */
export function normalizeLocation(url: URL): string {
  url.searchParams.delete("preview");
  const route = new URLSearchParams(url.hash.slice(1));
  if (
    route.get("page") === "explore" &&
    route.has("release") &&
    !["node", "relation", "dossier", "q", "person", "work", "trace"].some((k) =>
      route.has(k),
    )
  ) {
    route.delete("release");
    url.hash = route.toString();
  }
  return url.pathname + url.search + url.hash;
}
