import { test, expect } from "@playwright/test";
import { fetchText } from "../src/explore/network";

test("concurrent source retrieval shares four slots and cancels queued work", async () => {
  const original = globalThis.fetch;
  let active = 0, peak = 0;
  const calls: string[] = [];
  globalThis.fetch = async (input) => {
    calls.push(String(input));
    active++;
    peak = Math.max(peak, active);
    await new Promise((resolve) => setTimeout(resolve, 15));
    active--;
    return new Response("synthetic source passage");
  };
  try {
    const cancelled = new AbortController();
    const tasks = Array.from({ length: 9 }, (_, i) => fetchText(
      `https://example.org/fixture/${i}`, {},
      i === 8 ? cancelled.signal : new AbortController().signal,
    ));
    const outcomes = Promise.allSettled(tasks);
    cancelled.abort();
    const result = await outcomes;
    expect(peak).toBe(4);
    expect(calls).toHaveLength(8);
    expect(calls).not.toContain("https://example.org/fixture/8");
    expect(result.filter((value) => value.status === "fulfilled")).toHaveLength(8);
    // Cancellation cannot leak capacity into the next exploration.
    expect(await fetchText("https://example.org/next", {}, new AbortController().signal)).toBe("synthetic source passage");
  } finally {
    globalThis.fetch = original;
  }
});
