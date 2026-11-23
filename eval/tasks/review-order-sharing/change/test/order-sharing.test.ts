import { describe, expect, it } from 'vitest';
import { Cart } from '../src/cart.js';
import { OrderStore } from '../src/orders.js';
import { FakeGateway, ada, alice, bob, sampleCatalog } from './helpers.js';

async function aliceOrder() {
  const store = new OrderStore(sampleCatalog(), new FakeGateway());
  const cart = new Cart();
  cart.add('MUG', 1);
  const order = await store.place(alice, cart, null, new Date('2026-08-01T00:00:00Z'));
  return { store, order };
}

describe('order sharing', () => {
  it('lets a shared user see the order', async () => {
    const { store, order } = await aliceOrder();
    expect(store.get(bob, order.id)).toBeNull();
    store.share(alice, order.id, bob.id);
    expect(store.get(bob, order.id)?.id).toBe(order.id);
    expect(store.listFor(bob)).toHaveLength(1);
  });

  it("doesn't let a shared user refund", async () => {
    const { store, order } = await aliceOrder();
    store.share(alice, order.id, bob.id);
    await expect(store.refund(bob, order.id, 100)).rejects.toThrow();
    await store.refund(ada, order.id, 100);
  });
});
