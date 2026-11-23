import { type Cents, assertCents } from './money.js';

export interface PriceTier {
  minQuantity: number;
  unitPriceCents: Cents;
}

export interface Product {
  sku: string;
  name: string;
  priceCents: Cents;
  /** Units on hand. */
  stock: number;
  /** Lower unit prices from a minimum quantity. */
  tiers?: PriceTier[];
}

/** The unit price for a quantity: the highest tier that applies, else the normal price. */
export function unitPriceFor(product: Product, quantity: number): Cents {
  let best: PriceTier | null = null;
  for (const tier of product.tiers ?? []) {
    if (tier.minQuantity <= quantity && (best === null || tier.minQuantity > best.minQuantity)) {
      best = tier;
    }
  }
  if (best === null) {
    return product.priceCents;
  }
  return best.unitPriceCents;
}

/** Products by SKU. */
export class Catalog {
  private readonly products = new Map<string, Product>();

  add(product: Product): void {
    assertCents(product.priceCents, `price of ${product.sku}`);
    if (product.priceCents < 0) {
      throw new Error(`price of ${product.sku} can't be negative`);
    }
    const seen = new Set<number>();
    for (const tier of product.tiers ?? []) {
      assertCents(tier.unitPriceCents, `tier price of ${product.sku}`);
      if (tier.unitPriceCents < 0) {
        throw new Error(`tier price of ${product.sku} can't be negative`);
      }
      if (!Number.isInteger(tier.minQuantity) || tier.minQuantity < 2) {
        throw new Error(`tier minimum quantity of ${product.sku} must be a whole number of at least 2`);
      }
      if (seen.has(tier.minQuantity)) {
        throw new Error(`two tiers of ${product.sku} start at ${tier.minQuantity}`);
      }
      seen.add(tier.minQuantity);
    }
    if (this.products.has(product.sku)) {
      throw new Error(`duplicate SKU ${product.sku}`);
    }
    this.products.set(product.sku, { ...product, tiers: [...(product.tiers ?? [])] });
  }

  /** The product, or null when the SKU is unknown. */
  get(sku: string): Product | null {
    return this.products.get(sku) ?? null;
  }

  /** Removes units from stock. Throws if there aren't enough. */
  take(sku: string, quantity: number): void {
    const product = this.require(sku);
    if (quantity > product.stock) {
      throw new Error(`only ${product.stock} of ${sku} left`);
    }
    product.stock -= quantity;
  }

  /** Puts units back into stock. */
  putBack(sku: string, quantity: number): void {
    this.require(sku).stock += quantity;
  }

  private require(sku: string): Product {
    const product = this.products.get(sku);
    if (product === undefined) {
      throw new Error(`unknown SKU ${sku}`);
    }
    return product;
  }
}
