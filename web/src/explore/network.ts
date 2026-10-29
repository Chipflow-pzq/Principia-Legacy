/** All network destinations are chosen by code; source text cannot supply a tool URL. */
let active = 0;
const waiting: (() => void)[] = [];
function sourceSlot(signal: AbortSignal): Promise<() => void> {
  return new Promise((resolve, reject) => {
    const cancel = () => {
      const index = waiting.indexOf(start);
      if (index >= 0) waiting.splice(index, 1);
      reject(signal.reason || new DOMException("Cancelled", "AbortError"));
    };
    const start = () => {
      signal.removeEventListener("abort", cancel);
      if (signal.aborted) {
        cancel();
        waiting.shift()?.();
        return;
      }
      active++;
      resolve(() => {
        active--;
        waiting.shift()?.();
      });
    };
    if (signal.aborted) {
      cancel();
      return;
    }
    signal.addEventListener("abort", cancel, { once: true });
    if (active < 4) start();
    else waiting.push(start);
  });
}

export async function fetchText(
  url: string,
  init: RequestInit,
  signal: AbortSignal,
  timeout = 20000,
  maximum = 2_000_000,
): Promise<string> {
  const release = await sourceSlot(signal);
  try {
    return await readText(url, init, signal, timeout, maximum);
  } finally {
    release();
  }
}

async function readText(
  url: string,
  init: RequestInit,
  signal: AbortSignal,
  timeout: number,
  maximum: number,
) {
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
