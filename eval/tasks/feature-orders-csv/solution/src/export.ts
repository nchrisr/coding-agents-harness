import { type OrderStore } from './orders.js';
import { type User } from './users.js';

const HEADER = ['order_id', 'customer_id', 'placed_at', 'items', 'total', 'refunded'];

/** Dollars with two decimals and no sign, e.g. 2700 -> "27.00". */
function plainDollars(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

/** Quotes a field when it holds a comma, a double quote or a newline. */
function csvField(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}

/** The orders this user may see, as CSV, one row each, oldest first. */
export function exportOrdersCsv(store: OrderStore, user: User): string {
  let out = `${HEADER.join(',')}\n`;
  for (const order of store.listFor(user)) {
    const items: string[] = [];
    for (const line of order.lines) {
      items.push(`${line.sku} x ${line.quantity}`);
    }
    const fields = [
      order.id,
      order.customerId,
      order.placedAt.toISOString(),
      items.join('; '),
      plainDollars(order.totalCents),
      plainDollars(order.refundedCents),
    ];
    const quoted: string[] = [];
    for (const field of fields) {
      quoted.push(csvField(field));
    }
    out += `${quoted.join(',')}\n`;
  }
  return out;
}
