import { type Cents, assertCents } from './money.js';

export interface Product {
  sku: string;
  name: string;
  priceCents: Cents;
  /** Units on hand. */
  stock: number;
}

/** Products by SKU. */
export class Catalog {
  private readonly products = new Map<string, Product>();

  add(product: Product): void {
    assertCents(product.priceCents, `price of ${product.sku}`);
    if (product.priceCents < 0) {
      throw new Error(`price of ${product.sku} can't be negative`);
    }
    if (this.products.has(product.sku)) {
      throw new Error(`duplicate SKU ${product.sku}`);
    }
    this.products.set(product.sku, { ...product });
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
