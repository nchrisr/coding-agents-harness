import { describe, expect, it } from 'vitest';
import { Cart } from '../src/cart.js';
import { OrderStore } from '../src/orders.js';
import { FakeGateway, ada, alice, sampleCatalog } from './helpers.js';

describe('refunds are recorded after the gateway confirms', () => {
  it('shows nothing refunded while the gateway call is in flight', async () => {
    const gateway = new FakeGateway();
    const store = new OrderStore(sampleCatalog(), gateway);
    const cart = new Cart();
    cart.add('MUG', 1);
    const order = await store.place(alice, cart, null, new Date('2026-09-01T00:00:00Z'));
    gateway.delayMs = 20;
    const pending = store.refund(ada, order.id, 500);
    expect(store.get(ada, order.id)?.refundedCents).toBe(0);
    await pending;
    expect(store.get(ada, order.id)?.refundedCents).toBe(500);
  });
});
