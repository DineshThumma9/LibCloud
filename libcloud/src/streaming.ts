import { eventsLookUp, eventMessages, type EventEnvelope } from './schemas';

export interface StreamOptions {
  onEvent?: (type: string, data: any, envelope: EventEnvelope) => void;
  onStatusChange?: (statusText: string) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
  signal?: AbortSignal;
}

/**
 * Reads an SSE response body and emits typed events.
 */
export async function readSSEStream(
  response: Response,
  options: StreamOptions = {}
): Promise<void> {
  if (!response.body) {
    throw new Error("Response body is null or undefined");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processLine = (rawLine: string) => {
    const trimmed = rawLine.trim();
    if (!trimmed.startsWith("data:")) return;

    const jsonStr = trimmed.slice(5).trim();
    if (!jsonStr) return;

    try {
      const envelope: EventEnvelope = JSON.parse(jsonStr);
      const eventType = envelope?.type;
      const rawData = envelope?.data;

      // Validate data with schema if available (applies defaults automatically)
      const schema = eventsLookUp[eventType];
      const parsed = schema ? schema.safeParse(rawData ?? {}) : null;
      const validData = parsed && parsed.success ? parsed.data : (rawData ?? {});

      // Update ticker message if formatter exists
      const formatter = eventMessages[eventType];
      if (formatter && validData && options.onStatusChange) {
        const text = formatter(validData);
        if (text) options.onStatusChange(text);
      }

      if (options.onEvent) {
        options.onEvent(eventType, validData, envelope);
      }

      if (eventType === "done") {
        options.onDone?.();
      } else if (eventType === "error") {
        options.onError?.(new Error(rawData?.message || "Pipeline error"));
      }
    } catch (err) {
      console.warn("Failed to parse SSE JSON payload:", jsonStr, err);
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        processLine(line);
      }
    }

    if (buffer.trim()) {
      processLine(buffer);
    }
  } catch (err: any) {
    if (err?.name === "AbortError") {
      options.onStatusChange?.("Stream cancelled");
    } else {
      options.onError?.(err);
      throw err;
    }
  }
}
