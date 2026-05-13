export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function optionalString(value: unknown) {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

export function optionalStringOrNull(value: unknown) {
  if (value === null) {
    return null;
  }
  return optionalString(value);
}

export function numberOrDefault(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function nonNegativeIntegerOrDefault(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : fallback;
}

export function nonNegativeInteger(value: unknown) {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

export function assignOptionalNumbers<T extends object>(target: T, record: Record<string, unknown>, fields: string[]) {
  const writable = target as Record<string, unknown>;
  fields.forEach((field) => {
    const value = record[field];
    if (typeof value === "number" && Number.isFinite(value)) {
      writable[field] = value;
    }
  });
}

export function sanitizeNumberRecord(value: unknown): Record<string, number> | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  const clean = Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1])),
  );
  return Object.keys(clean).length ? clean : undefined;
}

export function stringArray(value: unknown) {
  return Array.isArray(value)
    ? value.flatMap((item) => {
        if (typeof item !== "string") {
          return [];
        }
        const trimmed = item.trim();
        return trimmed ? [trimmed] : [];
      })
    : [];
}
