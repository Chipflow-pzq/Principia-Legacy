/** All network destinations are chosen by code; source text cannot supply a tool URL. */
export async function fetchText(
  url: string,
  init: RequestInit,
  signal: AbortSignal,
  timeout = 20000,
  maximum = 2_000_000,
): Promise<string> {
  const requestSignal = AbortSignal.any([signal, AbortSignal.timeout(timeout)]);
  const response = await fetch(url, {
    ...init,
    signal: requestSignal,
    credentials: "omit",
    referrerPolicy: "no-referrer",
    redirect: "error",
  });
  if (!response.ok) {
    void response.body?.cancel().catch(() => {});
    throw new Error(`Request failed (HTTP ${response.status}).`);
  }
  if (
    !response.body ||
    Number(response.headers.get("content-length")) > maximum
  ) {
    void response.body?.cancel().catch(() => {});
    throw new Error("The service returned an oversized response.");
  }
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let bytes = 0,
    content = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maximum)
        throw new Error("The service returned an oversized response.");
      content += decoder.decode(value, { stream: true });
    }
    content += decoder.decode();
    return content;
  } finally {
    void reader.cancel().catch(() => {});
  }
}

export async function fetchJSON(
  url: string,
  init: RequestInit,
  signal: AbortSignal,
  timeout = 20000,
  maximum = 2_000_000,
): Promise<unknown> {
  return JSON.parse(await fetchText(url, init, signal, timeout, maximum));
}
