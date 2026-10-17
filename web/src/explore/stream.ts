import { object, text } from "./model";

/** Incremental SSE framing, including split UTF-8, CRLF and multiline data. */
export class EventDecoder {
  private pending = "";
  private data: string[] = [];
  private eventSize = 0;
  constructor(
    private emit: (data: string) => void,
    private maximumEvent = 262_144,
  ) {}
  push(chunk: string, final = false) {
    this.pending += chunk;
    let end: number;
    while ((end = this.pending.indexOf("\n")) >= 0) {
      const line = this.pending.slice(0, end).replace(/\r$/, "");
      this.pending = this.pending.slice(end + 1);
      this.line(line);
    }
    if (this.pending.length + this.eventSize > this.maximumEvent)
      throw new ProviderFailure(
        "The provider sent an oversized stream event. Received insights are retained.",
        false,
      );
    if (final) {
      if (this.pending) this.line(this.pending.replace(/\r$/, ""));
      this.pending = "";
      this.line("");
    }
  }
  private line(line: string) {
    if (line.length + this.eventSize > this.maximumEvent)
      throw new ProviderFailure(
        "The provider sent an oversized stream event. Received insights are retained.",
        false,
      );
    if (!line) {
      if (this.data.length) this.emit(this.data.join("\n"));
      this.data = [];
      this.eventSize = 0;
    } else if (line.startsWith("data:")) {
      this.eventSize += line.length;
      this.data.push(line.slice(5).replace(/^ /, ""));
    }
  }
}

export type StreamUpdate = {
  content: string;
  characters: number;
  firstContentMs: number | null;
  elapsedMs: number;
  transportBytes: number;
  events: number;
  reasoningCharacters: number;
};
export class ProviderFailure extends Error {
  constructor(
    message: string,
    readonly recoverable = true,
    readonly unsupported?: "format" | "thinking",
  ) {
    super(message);
  }
}

export type StreamLimits = {
  firstMs: number;
  idleMs: number;
  totalMs: number;
  bytes: number;
};

/** Each caller supplies a bounded wait; activity never extends the total deadline. */
export async function completionStream(options: {
  url: string;
  init: RequestInit;
  signal: AbortSignal;
  model: string;
  update: (value: StreamUpdate) => void;
  usage: (input: number | null, output: number | null) => void;
  limits?: StreamLimits;
}) {
  const limits = options.limits || {
    firstMs: 240_000,
    idleMs: 90_000,
    totalMs: 480_000,
    // SSE repeats JSON metadata for every token. This is a transport budget,
    // separate from the bounded text and single-event buffers held in memory.
    bytes: 32_000_000,
  };
  const watchdog = new AbortController(),
    start = Date.now();
  let timeoutMessage = `The provider has not started returning content for ${options.model} within ${Math.ceil(limits.firstMs / 1000)} seconds. Your sources are retained. Resume this step later, or choose another available model in Settings.`;
  let timer = setTimeout(() => watchdog.abort(), limits.firstMs);
  const totalTimer = setTimeout(() => {
    timeoutMessage = `This model request reached its ${Math.ceil(limits.totalMs / 1000)}-second limit. Completed work is retained; you can resume the unfinished step.`;
    watchdog.abort();
  }, limits.totalMs);
  const signal = AbortSignal.any([options.signal, watchdog.signal]);
  let content = "",
    firstContentMs: number | null = null,
    finish = "",
    done = false,
    bytes = 0,
    eventsReceived = 0,
    reasoningCharacters = 0,
    lastUpdate = 0;
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  const emit = (force = false) => {
    if (force || Date.now() - lastUpdate >= 250) {
      options.update({
        content,
        characters: content.length,
        firstContentMs,
        elapsedMs: Date.now() - start,
        transportBytes: bytes,
        events: eventsReceived,
        reasoningCharacters,
      });
      lastUpdate = Date.now();
    }
  };
  const consume = (raw: unknown, full = false) => {
    const value = object(raw);
    if (value.error)
      throw new ProviderFailure(
        "The provider interrupted its response. Completed work is retained; you can resume this step.",
      );
    if (value.model && value.model !== options.model)
      throw new ProviderFailure(
        "The provider returned a different model. The response was withheld.",
        false,
      );
    const usage = object(value.usage);
    if (Object.keys(usage).length)
      options.usage(
        Number.isInteger(usage.prompt_tokens)
          ? Number(usage.prompt_tokens)
          : null,
        Number.isInteger(usage.completion_tokens)
          ? Number(usage.completion_tokens)
          : null,
      );
    const choice = object(
      Array.isArray(value.choices) ? value.choices[0] : null,
    );
    const delta = object(full ? choice.message : choice.delta);
    const next = typeof delta.content === "string" ? delta.content : "";
    // Count reasoning for diagnostics without retaining or displaying its text.
    const reasoning =
      typeof delta.reasoning_content === "string"
        ? delta.reasoning_content
        : "";
    reasoningCharacters += reasoning.length;
    if (next.trim() || reasoning.trim()) {
      clearTimeout(timer);
      timeoutMessage =
        "The provider stopped sending data. Completed work is retained; you can resume this step.";
      timer = setTimeout(() => watchdog.abort(), limits.idleMs);
    }
    if (next) {
      if (firstContentMs === null) firstContentMs = Date.now() - start;
      content += next;
      if (/\s{2048}$/.test(content))
        throw new ProviderFailure(
          "The model stalled while formatting its answer. Complete insights are retained; no automatic retry was made. You can resume this step or choose another available model in Settings.",
        );
      if (content.length > 100_000)
        throw new ProviderFailure(
          "The model response exceeded the supported size.",
          false,
        );
      emit();
    } else if (reasoning) emit();
    if (choice.finish_reason) finish = text(choice.finish_reason, 40);
  };
  try {
    const response = await fetch(options.url, {
      ...options.init,
      signal,
      credentials: "omit",
      referrerPolicy: "no-referrer",
      redirect: "error",
    });
    if (!response.ok) {
      let unsupported: "format" | "thinking" | undefined;
      if ([400, 422].includes(response.status) && response.body) {
        // Inspect a small error body only to recognize rejected optional API fields.
        // Never surface provider messages, which may echo credentials or private input.
        const errorReader = response.body.getReader();
        let body = "";
        try {
          const decoder = new TextDecoder();
          while (body.length < 8192) {
            const part = await errorReader.read();
            if (part.done) break;
            body += decoder.decode(part.value).slice(0, 8192 - body.length);
          }
          if (
            /unsupported|not support|does not support|not allowed|不支持/i.test(
              body,
            )
          ) {
            if (/response_format|json_schema/i.test(body))
              unsupported = "format";
            else if (/enable_thinking|thinking_budget/i.test(body))
              unsupported = "thinking";
          }
        } finally {
          void errorReader.cancel().catch(() => {});
        }
      } else void response.body?.cancel().catch(() => {});
      throw new ProviderFailure(
        `Request failed (HTTP ${response.status}). ${[401, 403].includes(response.status) ? "Check your API key and account permissions." : response.status === 429 ? `The provider is limiting requests for ${options.model}. Wait before resuming, or choose another available model in Settings. Your completed work is retained; no automatic retry was made.` : "Your completed work is retained."}`,
        response.status === 408 || response.status >= 500,
        unsupported,
      );
    }
    if (!response.body)
      throw new ProviderFailure(
        "The provider returned an empty response. Your retrieved sources are retained.",
      );
    if (Number(response.headers.get("content-length")) > limits.bytes) {
      void response.body?.cancel().catch(() => {});
      throw new ProviderFailure(
        "The provider exceeded the stream transfer limit. Received insights are retained.",
        false,
      );
    }
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    const sse = response.headers
      .get("content-type")
      ?.toLowerCase()
      ?.includes("text/event-stream");
    let plain = "";
    const events = new EventDecoder((data) => {
      eventsReceived++;
      if (data.trim() === "[DONE]") {
        done = true;
        return;
      }
      if (!done) consume(JSON.parse(data));
    });
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      bytes += part.value.byteLength;
      if (bytes > (sse ? limits.bytes : Math.min(limits.bytes, 1_000_000)))
        throw new ProviderFailure(
          "The provider exceeded the response transfer limit. Received insights are retained.",
          false,
        );
      const chunk = decoder.decode(part.value, { stream: true });
      if (sse) events.push(chunk);
      else plain += chunk;
      if (done) break;
    }
    if (sse) events.push(decoder.decode(), true);
    else {
      consume(JSON.parse(plain + decoder.decode()), true);
      done = true;
    }
    emit(true);
    if (finish === "length")
      throw new ProviderFailure(
        "The response reached its output limit. The complete insights received so far are retained; resume to finish the map.",
      );
    if (!done && finish !== "stop")
      throw new ProviderFailure(
        "The model stream ended before completion. Your received insights are retained; resume this step.",
      );
    if (!content.trim())
      throw new ProviderFailure(
        "The provider returned no usable content. Your retrieved sources are retained.",
      );
    return { content, firstContentMs, elapsedMs: Date.now() - start };
  } catch (error) {
    emit(true);
    if (options.signal.aborted) throw options.signal.reason;
    if (watchdog.signal.aborted) throw new ProviderFailure(timeoutMessage);
    if (error instanceof ProviderFailure) throw error;
    throw new ProviderFailure(
      "The connection to the model was interrupted. Your completed work is retained; resume this step when ready.",
    );
  } finally {
    clearTimeout(timer);
    clearTimeout(totalTimer);
    // Cleanup must never become an unbounded sixth stage after the watchdogs stop.
    watchdog.abort();
    void reader?.cancel().catch(() => {});
  }
}

/** Read only fully closed JSON objects from a developing graph, never guess missing text. */
export function completedItems(
  content: string,
  key:
    | "nodes"
    | "relations"
    | "node_checks"
    | "relation_checks"
    | "backbone"
    | "branches"
    | "additions"
    | "map"
    | "result"
    | "roots"
    | "steps",
): unknown[] {
  const singleton =
    ["result", "roots", "steps"].includes(key) &&
    !new RegExp(`"${key}"\\s*:\\s*\\[`).test(content);
  const match = new RegExp(
    `"${key}"\\s*:\\s*${singleton ? "\\{" : "\\["}`,
  ).exec(content);
  if (!match) return [];
  const result: unknown[] = [];
  let depth = 0,
    quoted = false,
    escaped = false,
    start = -1;
  for (
    let i = match.index + match[0].length - Number(singleton);
    i < content.length;
    i++
  ) {
    const char = content[i];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') quoted = false;
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === "{") {
      if (depth++ === 0) start = i;
    } else if (char === "}" && depth > 0 && --depth === 0 && start >= 0) {
      try {
        result.push(JSON.parse(content.slice(start, i + 1)));
      } catch {
        /* incomplete or malformed: withhold */
      }
      start = -1;
      if (singleton) break;
      if (result.length >= (key === "nodes" || key === "node_checks" ? 24 : 48))
        break;
    } else if (char === "]" && depth === 0) break;
  }
  return result;
}
