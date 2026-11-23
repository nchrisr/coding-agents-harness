import { describe, expect, it } from 'vitest';
import { Cart } from '../src/cart.js';
import { OrderStore } from '../src/orders.js';
import { FakeGateway, ada, alice, bob, sam, sampleCatalog } from './helpers.js';

const now = new Date('2026-03-01T12:00:00Z');

function setup() {
  const catalog = sampleCatalog();
  const gateway = new FakeGateway();
  const store = new OrderStore(catalog, gateway);
  return { catalog, gateway, store };
}

function mugCart(quantity = 1): Cart {
  const cart = new Cart();
  cart.add('MUG', quantity);
  return cart;
}

describe('OrderStore.place', () => {
  it('charges, takes stock and records the order', async () => {
    const { catalog, gateway, store } = setup();
    const order = await store.place(alice, mugCart(2), null, now);
    expect(order.totalCents).toBe(2700);
    expect(gateway.charges).toEqual([{ customerId: 'u-alice', amountCents: 2700 }]);
    expect(catalog.get('MUG')?.stock).toBe(8);
  });

  it('puts stock back when the charge fails', async () => {
    const { catalog, gateway, store } = setup();
    gateway.failNext = true;
    await expect(store.place(alice, mugCart(2), null, now)).rejects.toThrow('card declined');
    expect(catalog.get('MUG')?.stock).toBe(10);
    expect(store.listFor(ada)).toEqual([]);
  });

  it('refuses more than is in stock', async () => {
    const { store } = setup();
    await expect(store.place(alice, mugCart(11), null, now)).rejects.toThrow(/only 10/);
  });
});

describe('who sees orders', () => {
  it('shows customers only their own orders; staff see all', async () => {
    const { store } = setup();
    const mine = await store.place(alice, mugCart(), null, now);
    await store.place(bob, mugCart(), null, now);
    expect(store.listFor(alice).map((o) => o.id)).toEqual([mine.id]);
    expect(store.get(bob, mine.id)).toBeNull();
    expect(store.listFor(sam)).toHaveLength(2);
  });
});

describe('OrderStore.refund', () => {
  it('lets an admin refund in parts, up to what was paid', async () => {
    const { gateway, store } = setup();
    const order = await store.place(alice, mugCart(), null, now);
    await store.refund(ada, order.id, 1000);
    await store.refund(ada, order.id, 350);
    expect(gateway.refunds).toHaveLength(2);
    await expect(store.refund(ada, order.id, 1)).rejects.toThrow(/more than what is left/);
  });

  it('refuses refunds from anyone but an admin', async () => {
    const { store } = setup();
    const order = await store.place(alice, mugCart(), null, now);
    await expect(store.refund(alice, order.id, 100)).rejects.toThrow();
    await expect(store.refund(sam, order.id, 100)).rejects.toThrow();
  });

  it('keeps nothing as refunded when the gateway fails', async () => {
    const { gateway, store } = setup();
    const order = await store.place(alice, mugCart(), null, now);
    gateway.failNext = true;
    await expect(store.refund(ada, order.id, 500)).rejects.toThrow('gateway down');
    expect(store.get(ada, order.id)?.refundedCents).toBe(0);
  });
});
