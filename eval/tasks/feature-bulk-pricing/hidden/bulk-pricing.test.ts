import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../../src/cart.js';
import { Catalog } from '../../src/catalog.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, alice } from '../helpers.js';

function tieredCatalog(): Catalog {
  const catalog = new Catalog();
  catalog.add({
    sku: 'CUP',
    name: 'Paper cup',
    priceCents: 100,
    stock: 1000,
    tiers: [
      { minQuantity: 50, unitPriceCents: 70 },
      { minQuantity: 10, unitPriceCents: 85 },
    ],
  });
  catalog.add({ sku: 'LID', name: 'Lid', priceCents: 30, stock: 1000 });
  return catalog;
}

function subtotal(catalog: Catalog, sku: string, quantity: number): number {
  const cart = new Cart();
  cart.add(sku, quantity);
  return cartTotals(catalog, cart, null).subtotalCents;
}

describe('bulk pricing', () => {
  it('uses the normal price below the first tier', () => {
    expect(subtotal(tieredCatalog(), 'CUP', 9)).toBe(900);
  });
  it('uses a tier from its minimum quantity', () => {
    expect(subtotal(tieredCatalog(), 'CUP', 10)).toBe(850);
    expect(subtotal(tieredCatalog(), 'CUP', 49)).toBe(4165);
  });
  it('uses the highest tier that applies, whatever order tiers are given in', () => {
    expect(subtotal(tieredCatalog(), 'CUP', 50)).toBe(3500);
    expect(subtotal(tieredCatalog(), 'CUP', 120)).toBe(8400);
  });
  it('prices the quantity after merging lines of the same SKU', () => {
    const cart = new Cart();
    cart.add('CUP', 6);
    cart.add('CUP', 6);
    expect(cartTotals(tieredCatalog(), cart, null).subtotalCents).toBe(1020);
  });
  it('leaves products without tiers alone', () => {
    expect(subtotal(tieredCatalog(), 'LID', 100)).toBe(3000);
  });
  it('applies discounts and tax to the tiered subtotal', () => {
    const cart = new Cart();
    cart.add('CUP', 10);
    const totals = cartTotals(tieredCatalog(), cart, { code: 'T', kind: 'percent', percent: 10 });
    expect(totals).toEqual({ subtotalCents: 850, discountCents: 85, taxCents: 61, totalCents: 826 });
  });
  it('charges the tiered total when an order is placed', async () => {
    const gateway = new FakeGateway();
    const store = new OrderStore(tieredCatalog(), gateway);
    const cart = new Cart();
    cart.add('CUP', 50);
    const order = await store.place(alice, cart, null, new Date('2026-05-01T00:00:00Z'));
    expect(order.totalCents).toBe(3780);
    expect(gateway.charges[0]?.amountCents).toBe(3780);
  });
});

describe('bulk pricing validation', () => {
  function addWithTiers(tiers: Array<{ minQuantity: number; unitPriceCents: number }>): void {
    new Catalog().add({ sku: 'X', name: 'X', priceCents: 100, stock: 1, tiers });
  }
  it('rejects a negative or fractional tier price', () => {
    expect(() => addWithTiers([{ minQuantity: 5, unitPriceCents: -1 }])).toThrow();
    expect(() => addWithTiers([{ minQuantity: 5, unitPriceCents: 9.5 }])).toThrow();
  });
  it('rejects a minimum quantity under 2 or not whole', () => {
    expect(() => addWithTiers([{ minQuantity: 1, unitPriceCents: 90 }])).toThrow();
    expect(() => addWithTiers([{ minQuantity: 0, unitPriceCents: 90 }])).toThrow();
    expect(() => addWithTiers([{ minQuantity: 2.5, unitPriceCents: 90 }])).toThrow();
  });
  it('rejects two tiers with the same minimum quantity', () => {
    expect(() =>
      addWithTiers([
        { minQuantity: 5, unitPriceCents: 90 },
        { minQuantity: 5, unitPriceCents: 80 },
      ]),
    ).toThrow();
  });
  it('accepts a free tier', () => {
    expect(() => addWithTiers([{ minQuantity: 100, unitPriceCents: 0 }])).not.toThrow();
  });
});
