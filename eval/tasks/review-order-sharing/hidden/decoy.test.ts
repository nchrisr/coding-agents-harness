import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, alice, sampleCatalog } from '../helpers.js';

describe('decoy: sharing with yourself does nothing, as the spec asks', () => {
  it('returns the order without an error and adds no one', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const cart = new Cart();
    cart.add('PEN', 1);
    const order = await store.place(alice, cart, null, new Date('2026-08-01T00:00:00Z'));
    expect(() => store.share(alice, order.id, alice.id)).not.toThrow();
    expect(store.get(alice, order.id)?.sharedWith).toEqual([]);
  });
});
