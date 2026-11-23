import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { type Discount } from '../../src/discounts.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, alice, bob, sampleCatalog } from '../helpers.js';

const noon = new Date('2026-07-01T12:00:00Z');

function setup() {
  const catalog = sampleCatalog();
  const gateway = new FakeGateway();
  const store = new OrderStore(catalog, gateway);
  return { catalog, gateway, store };
}

function pens(): Cart {
  const cart = new Cart();
  cart.add('PEN', 1);
  return cart;
}

function timesUsed(store: OrderStore, code: string): number {
  const fn = (store as unknown as Record<string, unknown>)['timesUsed'];
  if (typeof fn !== 'function') {
    throw new Error('OrderStore.timesUsed is missing');
  }
  return (fn as (code: string) => number).call(store, code);
}

describe('discount expiry', () => {
  const code = { code: 'SUMMER', kind: 'percent', percent: 10, expiresAt: noon } as Discount;

  it('works before it expires', async () => {
    const { store } = setup();
    const order = await store.place(alice, pens(), code, new Date('2026-07-01T11:59:59Z'));
    expect(order.totalCents).toBe(193);
  });

  it('is refused from the moment it expires, with nothing changed', async () => {
    const { catalog, gateway, store } = setup();
    await expect(store.place(alice, pens(), code, noon)).rejects.toThrow();
    expect(gateway.charges).toEqual([]);
    expect(catalog.get('PEN')?.stock).toBe(100);
    expect(timesUsed(store, 'SUMMER')).toBe(0);
  });

  it('leaves codes without an expiry alone', async () => {
    const { store } = setup();
    const forever = { code: 'ALWAYS', kind: 'fixed', amountCents: 50 } as Discount;
    const order = await store.place(alice, pens(), forever, new Date('2099-01-01T00:00:00Z'));
    expect(order.totalCents).toBe(161);
  });
});

describe('discount usage limits', () => {
  const once = { code: 'Once', kind: 'fixed', amountCents: 50, maxUses: 1 } as Discount;

  it('counts uses without regard to case, starting at 0', async () => {
    const { store } = setup();
    expect(timesUsed(store, 'once')).toBe(0);
    await store.place(alice, pens(), once, noon);
    expect(timesUsed(store, 'ONCE')).toBe(1);
    expect(timesUsed(store, 'never-seen')).toBe(0);
  });

  it('refuses a code used up, with nothing changed', async () => {
    const { catalog, gateway, store } = setup();
    await store.place(alice, pens(), once, noon);
    await expect(store.place(bob, pens(), once, noon)).rejects.toThrow();
    expect(gateway.charges).toHaveLength(1);
    expect(catalog.get('PEN')?.stock).toBe(99);
  });

  it("doesn't count a declined charge as a use", async () => {
    const { gateway, store } = setup();
    gateway.failNext = true;
    await expect(store.place(alice, pens(), once, noon)).rejects.toThrow('card declined');
    expect(timesUsed(store, 'Once')).toBe(0);
    await store.place(alice, pens(), once, noon);
    expect(timesUsed(store, 'Once')).toBe(1);
  });

  it('never goes over the limit when two orders are placed at once', async () => {
    const { gateway, store } = setup();
    gateway.delayMs = 20;
    const results = await Promise.allSettled([
      store.place(alice, pens(), once, noon),
      store.place(bob, pens(), once, noon),
    ]);
    let placed = 0;
    for (const result of results) {
      if (result.status === 'fulfilled') {
        placed += 1;
      }
    }
    expect(placed).toBe(1);
    expect(gateway.charges).toHaveLength(1);
    expect(timesUsed(store, 'once')).toBe(1);
  });

  it('allows exactly maxUses uses', async () => {
    const { store } = setup();
    const twice = { code: 'TWICE', kind: 'percent', percent: 5, maxUses: 2 } as Discount;
    await store.place(alice, pens(), twice, noon);
    await store.place(bob, pens(), twice, noon);
    await expect(store.place(alice, pens(), twice, noon)).rejects.toThrow();
    expect(timesUsed(store, 'twice')).toBe(2);
  });
});
