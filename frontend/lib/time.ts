// The backend stores UTC timestamps as "YYYY-MM-DD HH:MM:SS" (no zone marker).
// `new Date()` would read that as LOCAL time, so mark it as UTC first.
const BACKEND_TIMESTAMP = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

export function parseTimestamp(value: string): Date {
  return new Date(BACKEND_TIMESTAMP.test(value) ? `${value.replace(" ", "T")}Z` : value);
}

export function formatTime(value: string): string {
  const date = parseTimestamp(value);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Buckets a date for grouping the conversation history. */
export function historyBucket(value: string, now = new Date()): "Today" | "Yesterday" | "Previous 7 days" | "Earlier" {
  const date = parseTimestamp(value);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 24 * 60 * 60 * 1000;
  const time = date.getTime();
  if (time >= startOfToday) return "Today";
  if (time >= startOfToday - day) return "Yesterday";
  if (time >= startOfToday - 7 * day) return "Previous 7 days";
  return "Earlier";
}
