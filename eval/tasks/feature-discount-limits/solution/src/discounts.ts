import { type Cents, percentOf } from './money.js';

interface DiscountLimits {
  minSubtotalCents?: Cents;
  /** The code stops working at this moment. */
  expiresAt?: Date;
  /** How many orders may use the code. */
  maxUses?: number;
}

export type Discount =
  | ({ code: string; kind: 'percent'; percent: number } & DiscountLimits)
  | ({ code: string; kind: 'fixed'; amountCents: Cents } & DiscountLimits);

/** Discount codes, matched without regard to case. */
export class DiscountBook {
  private readonly discounts = new Map<string, Discount>();

  add(discount: Discount): void {
    this.discounts.set(discount.code.toUpperCase(), discount);
  }

  /** The discount for a code, or null when there's no such code. */
  find(code: string): Discount | null {
    return this.discounts.get(code.toUpperCase()) ?? null;
  }
}

/**
 * How much a discount takes off a subtotal. Never more than the subtotal, and 0 when the subtotal is
 * under the discount's minimum spend.
 */
export function discountAmount(discount: Discount, subtotalCents: Cents): Cents {
  if (discount.minSubtotalCents !== undefined && subtotalCents < discount.minSubtotalCents) {
    return 0;
  }
  let amount: Cents;
  if (discount.kind === 'percent') {
    amount = percentOf(subtotalCents, discount.percent);
  } else {
    amount = discount.amountCents;
  }
  return Math.min(amount, subtotalCents);
}
