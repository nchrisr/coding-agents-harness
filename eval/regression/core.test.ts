// The evaluation's own regression suite: existing behaviour the agent never sees, run after every
// task alongside the app's own tests. A test that passed before the run and fails after it is a
// regression.
import { describe, expect, it } from 'vitest';
import { canRefund, canViewOrder } from '../../src/access.js';
import { Cart, cartTotals } from '../../src/cart.js';
import { Catalog } from '../../src/catalog.js';
import { DiscountBook, discountAmount } from '../../src/discounts.js';
import { formatCents, percentOf } from '../../src/money.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, alice, bob, sam, sampleCatalog } from '../helpers.js';

const now = new Date('2026-04-02T09:30:00Z');

describe('core: money', () => {
  it('formats large and negative amounts', () => {
    expect(formatCents(123456789)).toBe('$1234567.89');
    expect(formatCents(-1)).toBe('-$0.01');
  });
  it('rounds percentages half up', () => {
    expect(percentOf(15, 10)).toBe(2);
    expect(percentOf(14, 10)).toBe(1);
    expect(percentOf(0, 50)).toBe(0);
  });
});

describe('core: catalog', () => {
  it('rejects bad products', () => {
    const catalog = new Catalog();
    expect(() => catalog.add({ sku: 'X', name: 'X', priceCents: 1.5, stock: 1 })).toThrow();
    expect(() => catalog.add({ sku: 'X', name: 'X', priceCents: -1, stock: 1 })).toThrow();
    catalog.add({ sku: 'X', name: 'X', priceCents: 0, stock: 1 });
    expect(() => catalog.add({ sku: 'X', name: 'Y', priceCents: 1, stock: 1 })).toThrow(/duplicate/);
  });
  it('returns null for an unknown SKU', () => {
    expect(sampleCatalog().get('NOPE')).toBeNull();
  });
  it('keeps its own copy of a product', () => {
    const catalog = new Catalog();
    const product = { sku: 'K', name: 'K', priceCents: 100, stock: 3 };
    catalog.add(product);
    product.stock = 99;
    expect(catalog.get('K')?.stock).toBe(3);
  });
});

describe('core: discounts and totals', () => {
  it('matches codes without regard to case', () => {
    const book = new DiscountBook();
    book.add({ code: 'Spring', kind: 'percent', percent: 20 });
    expect(book.find('SPRING')).not.toBeNull();
    expect(book.find('summer')).toBeNull();
  });
  it('caps a discount at the subtotal', () => {
    expect(discountAmount({ code: 'A', kind: 'fixed', amountCents: 900 }, 500)).toBe(500);
    expect(discountAmount({ code: 'B', kind: 'percent', percent: 100 }, 777)).toBe(777);
  });
  it('applies minimum spend at the boundary', () => {
    const d = { code: 'M', kind: 'fixed' as const, amountCents: 100, minSubtotalCents: 1000 };
    expect(discountAmount(d, 999)).toBe(0);
    expect(discountAmount(d, 1000)).toBe(100);
  });
  it('taxes the discounted subtotal', () => {
    const cart = new Cart();
    cart.add('TEE', 2);
    const totals = cartTotals(sampleCatalog(), cart, { code: 'F', kind: 'fixed', amountCents: 998 });
    expect(totals).toEqual({ subtotalCents: 3998, discountCents: 998, taxCents: 240, totalCents: 3240 });
  });
  it('handles a free product', () => {
    const catalog = new Catalog();
    catalog.add({ sku: 'FREE', name: 'Sticker', priceCents: 0, stock: 5 });
    const cart = new Cart();
    cart.add('FREE', 3);
    expect(cartTotals(catalog, cart, null).totalCents).toBe(0);
  });
});

describe('core: access', () => {
  it('lets customers see only their own orders and only admins refund', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const cart = new Cart();
    cart.add('PEN', 1);
    const order = await store.place(alice, cart, null, now);
    expect(canViewOrder(alice, order)).toBe(true);
    expect(canViewOrder(bob, order)).toBe(false);
    expect(canViewOrder(sam, order)).toBe(true);
    expect(canRefund(alice, order)).toBe(false);
    expect(canRefund(sam, order)).toBe(false);
    expect(canRefund(ada, order)).toBe(true);
  });
});

describe('core: orders', () => {
  it('refuses an empty cart', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    await expect(store.place(alice, new Cart(), null, now)).rejects.toThrow(/empty/);
  });
  it('gives each order its own id and keeps them oldest first', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const cart = new Cart();
    cart.add('PEN', 1);
    const first = await store.place(alice, cart, null, now);
    const second = await store.place(alice, cart, null, now);
    expect(first.id).not.toBe(second.id);
    expect(store.listFor(alice).map((o) => o.id)).toEqual([first.id, second.id]);
    expect(store.listFor(alice)[0]?.placedAt.toISOString()).toBe('2026-04-02T09:30:00.000Z');
  });
  it('rolls back every line when one is out of stock', async () => {
    const catalog = sampleCatalog();
    const store = new OrderStore(catalog, new FakeGateway());
    const cart = new Cart();
    cart.add('MUG', 2);
    cart.add('TEE', 6);
    await expect(store.place(alice, cart, null, now)).rejects.toThrow();
    expect(catalog.get('MUG')?.stock).toBe(10);
  });
  it('refuses zero, negative and fractional refunds, and unknown orders', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const cart = new Cart();
    cart.add('PEN', 1);
    const order = await store.place(alice, cart, null, now);
    await expect(store.refund(ada, order.id, 0)).rejects.toThrow();
    await expect(store.refund(ada, order.id, -5)).rejects.toThrow();
    await expect(store.refund(ada, order.id, 1.5)).rejects.toThrow();
    await expect(store.refund(ada, 'order-999', 1)).rejects.toThrow();
  });
  it('refunds the whole order exactly', async () => {
    const gateway = new FakeGateway();
    const store = new OrderStore(sampleCatalog(), gateway);
    const cart = new Cart();
    cart.add('PEN', 1);
    const order = await store.place(alice, cart, null, now);
    await store.refund(ada, order.id, order.totalCents);
    expect(store.get(ada, order.id)?.refundedCents).toBe(order.totalCents);
    expect(gateway.refunds).toEqual([{ chargeId: order.chargeId, amountCents: order.totalCents }]);
  });
});
