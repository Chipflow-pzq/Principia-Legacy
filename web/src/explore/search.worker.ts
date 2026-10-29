import type { Entry, Index } from "./indexTypes";
import { rankEntries } from "./ranking";

let entries: Entry[] = [];
self.onmessage = (event: MessageEvent) => {
  const message = event.data;
  if (message.type === "init") {
    entries = message.entries;
    self.postMessage({ id: message.id, ready: true });
  } else if (message.type === "rank") {
    const found = rankEntries(
      { entries } as Index,
      message.query,
      message.limit,
      message.subjects,
    );
    self.postMessage({ id: message.id, ids: found.map((entry) => entry.id) });
  }
};
