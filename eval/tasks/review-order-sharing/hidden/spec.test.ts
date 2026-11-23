import { describe, expect, it } from 'vitest';
import { canRefund } from '../../src/access.js';
import { Cart } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, alice, bob, sampleCatalog } from '../helpers.js';

describe('spec still met: order sharing', () => {
  it('lets the customer share, once per user, and the shared user view only', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const cart = new Cart();
    cart.add('PEN', 1);
    const order = await store.place(alice, cart, null, new Date('2026-08-01T00:00:00Z'));
    store.share(alice, order.id, bob.id);
    store.share(alice, order.id, bob.id);
    const seen = store.get(bob, order.id);
    expect(seen?.sharedWith).toEqual([bob.id]);
    expect(store.listFor(bob).map((o) => o.id)).toEqual([order.id]);
    expect(seen === null ? true : canRefund(bob, seen)).toBe(false);
    await expect(store.refund(bob, order.id, 10)).rejects.toThrow();
    await store.refund(ada, order.id, 10);
  });
  it('refuses to share an order that does not exist', () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    expect(() => store.share(alice, 'order-404', bob.id)).toThrow();
  });
});
