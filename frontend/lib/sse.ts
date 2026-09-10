// Shared SSE frame parser. Both the chat stream and the research stream speak the
// same `event: X\ndata: {json}\n\n` format, so they share one parser rather than
// keeping two copies in sync.

export interface SseEvent {
  event: string;
  data: string;
}

/** Pulls complete "event: X\ndata: Y\n\n" frames out of a growing text buffer. */
export function extractSseEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  let rest = buffer;

  let sepIndex: number;
  while ((sepIndex = rest.indexOf("\n\n")) !== -1) {
    const rawFrame = rest.slice(0, sepIndex);
    rest = rest.slice(sepIndex + 2);

    let eventType = "message";
    let dataLine = "";
    for (const line of rawFrame.split("\n")) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
    }
    if (dataLine) events.push({ event: eventType, data: dataLine });
  }

  return { events, rest };
}

/** Safely JSON-parse a frame's data payload; returns null on malformed input. */
export function parseSseData<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}
