/** A deep merge of overrides onto defaults, as a new object; neither argument changes. */
export function mergeSettings<T extends object>(defaults: T, overrides: Partial<T>): T {
  return mergeInto(structuredClone(defaults), overrides) as T;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function mergeInto(target: object, source: object): object {
  const out = target as Record<string, unknown>;
  for (const [key, value] of Object.entries(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      continue;
    }
    const current = out[key];
    if (isPlainObject(current) && isPlainObject(value)) {
      out[key] = mergeInto(current, value);
    } else {
      out[key] = structuredClone(value);
    }
  }
  return out;
}
