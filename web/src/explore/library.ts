import { importExploration, type Exploration, type Registry } from "./model";

const DATABASE = "principia-personal-explorations";
async function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("maps", { keyPath: "id" });
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
  action: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await database();
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction("maps", mode),
        request = action(transaction.objectStore("maps"));
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
export async function savedMaps(registry: Registry): Promise<Exploration[]> {
  const values = await operation<Exploration[]>("readonly", (store) =>
    store.getAll(),
  );
  return values
    .map((v) => importExploration(JSON.stringify(v), registry))
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}
export async function saveMap(draft: Exploration, registry: Registry) {
  const clean = importExploration(JSON.stringify(draft), registry);
  await operation("readwrite", (store) => store.put(clean));
}
export async function deleteMap(id: string) {
  await operation("readwrite", (store) => store.delete(id));
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
