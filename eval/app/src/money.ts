/** Whole cents. Money is never a float in this library. */
export type Cents = number;

/** Throws unless the value is a whole number of cents. */
export function assertCents(value: number, what: string): void {
  if (!Number.isInteger(value)) {
    throw new Error(`${what} must be whole cents, got ${value}`);
  }
}

/** Formats cents as dollars, e.g. 1234 -> "$12.34" and -50 -> "-$0.50". */
export function formatCents(cents: Cents): string {
  assertCents(cents, 'amount');
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const rest = String(abs % 100).padStart(2, '0');
  return `${sign}$${dollars}.${rest}`;
}

/**
 * A percentage of an amount, rounded half up to whole cents.
 * percentOf(1999, 10) === 200.
 */
export function percentOf(cents: Cents, percent: number): Cents {
  assertCents(cents, 'amount');
  return Math.round((cents * percent) / 100);
}
