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

export function readerOptions(route: URLSearchParams, allowedLayers: string[]) {
  const bounded = (name: string, fallback: number, min: number, max: number) =>
    Math.max(min, Math.min(max, Number(route.get(name)) || fallback));
  return {
    human: route.get("human") === "1",
    depth: bounded("depth", 40, 40, 200),
    hops: bounded("hops", 1, 1, 6),
    view: route.get("view") === "list" ? ("list" as const) : ("map" as const),
    layers: route.has("layers")
      ? (route.get("layers") || "")
          .split(",")
          .filter((l) => allowedLayers.includes(l))
      : allowedLayers,
    direction: ["ancestors", "descendants"].includes(
      route.get("direction") || "",
    )
      ? route.get("direction")!
      : "both",
    area: route.get("area") || "",
    coverage: ["available", "pending", "ready"].includes(
      route.get("coverage") || "",
    )
      ? route.get("coverage")!
      : "all",
    catalogOffset: bounded("catalogoffset", 0, 0, 10_000_000),
  };
}

export function rememberReadingPosition() {
  history.replaceState(
    {
      ...history.state,
      readerPosition: {
        y: window.scrollY,
        focus: document.activeElement?.id || "",
      },
    },
    "",
  );
}

export function restoreReadingPosition() {
  const position = history.state?.readerPosition;
  if (!position) return;
  const route = location.hash;
  let stopped = false;
  const observer = new MutationObserver(restore);
  const timer = window.setTimeout(() => {
    restore();
    stop();
  }, 15000);
  function stop() {
    stopped = true;
    observer.disconnect();
    clearTimeout(timer);
    window.removeEventListener("wheel", stop);
    window.removeEventListener("pointerdown", stop);
    window.removeEventListener("keydown", stop);
  }
  function restore() {
    if (stopped || location.hash !== route) {
      stop();
      return;
    }
    const target = position.focus
      ? document.getElementById(position.focus)
      : null;
    window.scrollTo({ top: position.y });
    if (target) {
      // A second snapshot-bound response may replace this card after the first
      // render. Keep restoring until the bounded window ends or the reader acts.
      target.focus({ preventScroll: true });
    } else if (
      !position.focus &&
      document.documentElement.scrollHeight >= position.y + innerHeight
    )
      stop();
  }
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener("wheel", stop, { once: true });
  window.addEventListener("pointerdown", stop, { once: true });
  window.addEventListener("keydown", stop, { once: true });
  requestAnimationFrame(restore);
}
