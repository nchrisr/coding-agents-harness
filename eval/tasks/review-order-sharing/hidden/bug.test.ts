import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, alice, bob, sam, sampleCatalog } from '../helpers.js';

const carol = { id: 'u-carol', name: 'Carol', role: 'customer' as const };

async function shared() {
  const store = new OrderStore(sampleCatalog(), new FakeGateway());
  const cart = new Cart();
  cart.add('MUG', 1);
  const order = await store.place(alice, cart, null, new Date('2026-08-01T00:00:00Z'));
  store.share(alice, order.id, bob.id);
  return { store, order };
}

describe("planted bug: only the order's customer can share it", () => {
  it("stops a user it was shared with from sharing it on", async () => {
    const { store, order } = await shared();
    expect(() => store.share(bob, order.id, carol.id)).toThrow();
    expect(store.get(carol, order.id)).toBeNull();
  });
  it("stops staff sharing a customer's order", async () => {
    const { store, order } = await shared();
    expect(() => store.share(sam, order.id, carol.id)).toThrow();
    expect(store.get(carol, order.id)).toBeNull();
  });
});
