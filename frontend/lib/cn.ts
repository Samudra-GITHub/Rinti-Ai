type ClassValue = string | number | null | false | undefined | ClassValue[];

function flatten(input: ClassValue, out: string[]) {
  if (!input) return;
  if (Array.isArray(input)) {
    input.forEach((v) => flatten(v, out));
    return;
  }
  out.push(String(input));
}

export function cn(...inputs: ClassValue[]): string {
  const out: string[] = [];
  flatten(inputs, out);
  return out.join(" ");
}
