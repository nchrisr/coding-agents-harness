import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, alice, sampleCatalog } from '../helpers.js';

describe('planted bug: two refunds at once never refund more than was paid', () => {
  it('refuses the second of two overlapping refunds that together exceed the total', async () => {
    const gateway = new FakeGateway();
    const store = new OrderStore(sampleCatalog(), gateway);
    const cart = new Cart();
    cart.add('MUG', 1);
    const order = await store.place(alice, cart, null, new Date('2026-09-01T00:00:00Z'));
    gateway.delayMs = 20;
    const results = await Promise.allSettled([
      store.refund(ada, order.id, 800),
      store.refund(ada, order.id, 800),
    ]);
    let refunded = 0;
    for (const call of gateway.refunds) {
      refunded += call.amountCents;
    }
    expect(refunded).toBeLessThanOrEqual(order.totalCents);
    expect(store.get(ada, order.id)?.refundedCents).toBeLessThanOrEqual(order.totalCents);
    let rejected = 0;
    for (const result of results) {
      if (result.status === 'rejected') {
        rejected += 1;
      }
    }
    expect(rejected).toBe(1);
  });
});
