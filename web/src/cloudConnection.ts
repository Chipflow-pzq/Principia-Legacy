// Only atlas GET reads use this recovery path. Provider generations are never retried here.
let knownCloud = false;
const waiting = new Set<symbol>();
const listeners = new Set<(reconnecting: boolean) => void>();
function notify() {
  for (const listener of listeners) listener(waiting.size > 0);
}
export function watchCloudConnection(
  listener: (reconnecting: boolean) => void,
) {
  listeners.add(listener);
  listener(waiting.size > 0);
  return () => {
    listeners.delete(listener);
  };
}
function delay(milliseconds: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    signal?.throwIfAborted();
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, milliseconds);
    signal?.addEventListener("abort", abort, { once: true });
  });
}
export async function readAtlas(url: string, signal?: AbortSignal) {
  const request = Symbol();
  let attempt = 0;
  try {
    while (true) {
      signal?.throwIfAborted();
      let response: Response;
      let text: string;
      try {
        response = await fetch(url, {
          signal: AbortSignal.any([
            ...(signal ? [signal] : []),
            AbortSignal.timeout(15000),
          ]),
        });
        text = await response.text();
      } catch (error) {
        signal?.throwIfAborted();
        // A supervised local reader can restart while the page stays open.
        if (!knownCloud && attempt >= 2) throw error;
        if (knownCloud) {
          waiting.add(request);
          notify();
        }
        await delay(Math.min(1000 * 2 ** attempt++, 4000), signal);
        continue;
      }
      const data = JSON.parse(text);
      if (data.connection_mode === "private_cloud") knownCloud = true;
      if (response.status === 503 && data.code === "cloud_reconnecting") {
        knownCloud = true;
        waiting.add(request);
        notify();
        await delay(Math.min(1000 * 2 ** attempt++, 4000), signal);
        continue;
      }
      if (!response.ok)
        throw new Error(
          data.error || "The reader could not complete this request.",
        );
      return { data, text };
    }
  } finally {
    waiting.delete(request);
    notify();
  }
}
