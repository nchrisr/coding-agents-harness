import { type Catalog } from './catalog.js';
import { type Discount, discountAmount } from './discounts.js';
import { type Cents, percentOf } from './money.js';

export interface CartLine {
  sku: string;
  quantity: number;
}

export interface CartTotals {
  subtotalCents: Cents;
  discountCents: Cents;
  taxCents: Cents;
  totalCents: Cents;
}

/** Sales tax, applied to the subtotal after discounts. */
export const TAX_PERCENT = 8;

/** A shopper's cart: SKUs and quantities. Adding the same SKU twice adds to its quantity. */
export class Cart {
  private readonly quantities = new Map<string, number>();

  add(sku: string, quantity: number): void {
    if (!Number.isInteger(quantity) || quantity <= 0) {
      throw new Error(`quantity must be a positive whole number, got ${quantity}`);
    }
    this.quantities.set(sku, (this.quantities.get(sku) ?? 0) + quantity);
  }

  remove(sku: string): void {
    this.quantities.delete(sku);
  }

  lines(): CartLine[] {
    const lines: CartLine[] = [];
    for (const [sku, quantity] of this.quantities) {
      lines.push({ sku, quantity });
    }
    return lines;
  }

  isEmpty(): boolean {
    return this.quantities.size === 0;
  }
}

/** The price of one line: unit price times quantity. */
export function linePriceCents(catalog: Catalog, line: CartLine): Cents {
  const product = catalog.get(line.sku);
  if (product === null) {
    throw new Error(`unknown SKU ${line.sku}`);
  }
  return product.priceCents * line.quantity;
}

/** Totals for a cart, with an optional discount. Tax is on the discounted subtotal. */
export function cartTotals(catalog: Catalog, cart: Cart, discount: Discount | null): CartTotals {
  let subtotalCents = 0;
  for (const line of cart.lines()) {
    subtotalCents += linePriceCents(catalog, line);
  }
  let discountCents = 0;
  if (discount !== null) {
    discountCents = discountAmount(discount, subtotalCents);
  }
  const taxCents = percentOf(subtotalCents - discountCents, TAX_PERCENT);
  return {
    subtotalCents,
    discountCents,
    taxCents,
    totalCents: subtotalCents - discountCents + taxCents,
  };
}
