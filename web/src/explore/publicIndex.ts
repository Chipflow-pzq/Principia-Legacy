import { api } from "../types";
import type { Entry, Index } from "./indexTypes";
import { rankEntries } from "./ranking";
import { atlasSource } from "./sources";

type Shard = { id: string; total: number; hash: string; pillar: string };
type Manifest = {
  release_id: string;
  snapshot_hash: string;
  total: number;
  shards: Shard[];
};
let cachedIndex: Index | null = null;
let sequence = 0;

async function cache(key: string, value?: string): Promise<string | undefined> {
  // Public material only. Failure to cache must not prevent research.
  return new Promise((resolve) => {
    const request = indexedDB.open("principia-public-index", 2);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains("shards"))
        request.result.createObjectStore("shards");
    };
    request.onerror = request.onblocked = () => resolve(undefined);
    request.onsuccess = () => {
      const db = request.result;
      const tx = db.transaction(
        "shards",
        value === undefined ? "readonly" : "readwrite",
      );
      const store = tx.objectStore("shards");
      const op = value === undefined ? store.get(key) : store.put(value, key);
      tx.oncomplete = () => {
        db.close();
        resolve(typeof op.result === "string" ? op.result : undefined);
      };
      tx.onerror = tx.onabort = () => {
        db.close();
        resolve(undefined);
      };
    };
  });
}

async function hash(value: string) {
  const bytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return [...new Uint8Array(bytes)]
    .map((n) => n.toString(16).padStart(2, "0"))
    .join("");
}

async function pruneCache(retain: string[]) {
  // Keep this snapshot only, with a 128 MiB string budget. Public shards can be
  // downloaded again; personal saved maps use a separate database and are untouched.
  const allowed = new Set(retain);
  await new Promise<void>((resolve) => {
    const request = indexedDB.open("principia-public-index", 2);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains("shards"))
        request.result.createObjectStore("shards");
    };
    request.onerror = request.onblocked = () => resolve();
    request.onsuccess = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("shards")) {
        db.close();
        resolve();
        return;
      }
      const tx = db.transaction("shards", "readwrite");
      let bytes = 0;
      const cursor = tx.objectStore("shards").openCursor();
      cursor.onsuccess = () => {
        const row = cursor.result;
        if (!row) return;
        const size =
          typeof row.value === "string" ? row.value.length * 2 : Infinity;
        if (!allowed.has(String(row.key)) || bytes + size > 128 * 1024 * 1024)
          row.delete();
        else bytes += size;
        row.continue();
      };
      tx.oncomplete =
        tx.onerror =
        tx.onabort =
          () => {
            db.close();
            resolve();
          };
    };
  });
}

export async function atlasIndex(
  release: string,
  signal: AbortSignal,
  progress: (loaded: number, total: number) => void = () => {},
): Promise<Index> {
  const manifest = await api<Manifest>(
    "exploration-manifest",
    { release },
    signal,
  );
  if (cachedIndex?.snapshot_hash === manifest.snapshot_hash) {
    progress(manifest.total, manifest.total);
    return cachedIndex;
  }
  const entries: Entry[] = [];
  const pending = [...manifest.shards];
  async function load() {
    while (pending.length) {
      signal.throwIfAborted();
      const shard = pending.shift()!;
      let payload = await cache(shard.hash);
      if (!payload || (await hash(payload)) !== shard.hash) {
        const response = await api<{
          snapshot_hash: string;
          hash: string;
          payload: string;
        }>(
          "exploration-shard",
          { release: manifest.release_id, shard: shard.id },
          signal,
        );
        if (
          response.snapshot_hash !== manifest.snapshot_hash ||
          response.hash !== shard.hash ||
          (await hash(response.payload)) !== shard.hash
        )
          throw new Error(
            "The atlas changed while its index was loading. Please retry.",
          );
        payload = response.payload;
        await cache(shard.hash, payload);
      }
      const rows: Entry[] = JSON.parse(payload);
      if (!Array.isArray(rows) || rows.length !== shard.total)
        throw new Error("Incomplete public search shard.");
      entries.push(...rows);
      progress(entries.length, manifest.total);
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, pending.length) }, load));
  await pruneCache(manifest.shards.map((s) => s.hash));
  signal.throwIfAborted();
  cachedIndex?.worker?.terminate();
  const worker = new Worker(new URL("./search.worker.ts", import.meta.url), {
    type: "module",
  });
  worker.postMessage({ type: "init", entries, id: ++sequence });
  cachedIndex = { ...manifest, entries, worker };
  return cachedIndex;
}

async function hydrate(index: Index, ids: string[], signal?: AbortSignal) {
  signal?.throwIfAborted();
  const selected = new Set(ids);
  const missing = index.entries.filter((e) => selected.has(e.id) && e.compact);
  for (let offset = 0; offset < missing.length; offset += 40) {
    const response = await api<Index>(
      "exploration-records",
      {
        release: index.release_id,
        ids: missing
          .slice(offset, offset + 40)
          .map((e) => e.id)
          .join(","),
      },
      signal,
    );
    if (response.snapshot_hash !== index.snapshot_hash)
      throw new Error(
        "The atlas snapshot changed before evidence could be read.",
      );
    for (const full of response.entries) {
      const original = missing.find((e) => e.id === full.id);
      if (
        !original ||
        original.content_hash !== full.content_hash ||
        original.revision !== full.revision
      )
        throw new Error(
          "Atlas evidence does not match the pinned search record.",
        );
      Object.assign(original, full, { compact: false });
    }
  }
  return ids
    .map((id) => index.entries.find((e) => e.id === id))
    .filter((e): e is Entry => Boolean(e && !e.compact));
}

export async function hydrateAtlas(
  index: Index,
  id: string,
  signal?: AbortSignal,
) {
  return (await hydrate(index, [id], signal))[0];
}

export async function matchAtlas(
  index: Index,
  query: string,
  limit = 8,
  subjects: string[] = [],
  signal?: AbortSignal,
) {
  const ids = index.worker
    ? await new Promise<string[]>((resolve, reject) => {
        const id = ++sequence;
        const worker = index.worker!;
        const timer = setTimeout(
          () =>
            finish(new Error("Local atlas matching exceeded its time limit.")),
          10000,
        );
        const abort = () => finish(new DOMException("Cancelled", "AbortError"));
        const error = () =>
          finish(new Error("Local atlas matching could not finish."));
        const receive = (event: MessageEvent) => {
          if (event.data.id === id) finish(null, event.data.ids);
        };
        function finish(error: Error | null, result: string[] = []) {
          clearTimeout(timer);
          worker.removeEventListener("message", receive);
          worker.removeEventListener("error", errorHandler);
          signal?.removeEventListener("abort", abort);
          if (error) reject(error);
          else resolve(result);
        }
        const errorHandler = error;
        worker.addEventListener("message", receive);
        worker.addEventListener("error", errorHandler);
        signal?.addEventListener("abort", abort, { once: true });
        if (signal?.aborted) {
          abort();
          return;
        }
        worker.postMessage({ type: "rank", id, query, limit, subjects });
      })
    : rankEntries(index, query, limit, subjects).map((e) => e.id);
  return (await hydrate(index, ids, signal)).map(atlasSource);
}

export async function hydrateRelated(
  index: Index,
  ids: string[],
  signal?: AbortSignal,
) {
  return (await hydrate(index, ids, signal)).map(atlasSource);
}
