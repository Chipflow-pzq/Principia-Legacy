import { importExploration, type Exploration, type Registry } from "./model";

export type SavedMap = Pick<Exploration, "id" | "title" | "created_at"> & {
  fingerprint: string;
};
export function fingerprint(value: Exploration) {
  const text = JSON.stringify(value);
  // UI dirty-state hint only; import validation remains the trust boundary.
  let a = 2166136261,
    b = 5381;
  for (let i = 0; i < text.length; i++) {
    a = Math.imul(a ^ text.charCodeAt(i), 16777619);
    b = Math.imul(b, 33) ^ text.charCodeAt(i);
  }
  return `${text.length}:${a >>> 0}:${b >>> 0}`;
}
function metadata(map: Exploration): SavedMap {
  return {
    id: map.id,
    title: map.title,
    created_at: map.created_at,
    fingerprint: fingerprint(map),
  };
}
const DATABASE = "principia-personal-explorations";
async function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 2);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("maps"))
        db.createObjectStore("maps", { keyPath: "id" });
      const index = db.createObjectStore("metadata", { keyPath: "id" });
      index.createIndex("created_at", "created_at");
      const cursor = request.transaction!.objectStore("maps").openCursor();
      cursor.onsuccess = () => {
        if (cursor.result) {
          const map = cursor.result.value;
          if (
            typeof map?.id === "string" &&
            typeof map?.title === "string" &&
            typeof map?.created_at === "string"
          )
            index.put(metadata(map));
          cursor.result.continue();
        }
      };
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(
        new Error(
          "Browser storage is unavailable. Download a JSON file instead.",
        ),
      );
    request.onblocked = () =>
      reject(
        new Error(
          "Another tab is blocking local storage. Close that tab and try again.",
        ),
      );
  });
}
async function operation<T>(
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore, metadata: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await database();
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction(["maps", "metadata"], mode),
        request = action(
          transaction.objectStore("maps"),
          transaction.objectStore("metadata"),
        );
      transaction.oncomplete = () => resolve(request.result);
      transaction.onerror = transaction.onabort = () =>
        reject(
          new Error(
            "This device could not save the map. Download a JSON file to keep it.",
          ),
        );
    });
  } finally {
    db.close();
  }
}
export async function savedMaps(_registry: Registry): Promise<SavedMap[]> {
  const values = await operation<SavedMap[]>("readonly", (_store, metadata) =>
    metadata.getAll(),
  );
  return values.sort((a, b) => b.created_at.localeCompare(a.created_at));
}
export async function loadMap(
  id: string,
  registry: Registry,
): Promise<Exploration> {
  const value = await operation<Exploration>("readonly", (store) =>
    store.get(id),
  );
  if (!value) throw new Error("This map is no longer saved on this device.");
  return importExploration(JSON.stringify(value), registry);
}
export async function saveMap(draft: Exploration, registry: Registry) {
  const clean = importExploration(JSON.stringify(draft), registry);
  await operation("readwrite", (store, index) => {
    index.put(metadata(clean));
    return store.put(clean);
  });
}
export async function deleteMap(id: string) {
  await operation("readwrite", (store, index) => {
    index.delete(id);
    return store.delete(id);
  });
}
export function downloadMap(draft: Exploration) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `principia-exploration-${draft.id.slice(0, 8)}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
