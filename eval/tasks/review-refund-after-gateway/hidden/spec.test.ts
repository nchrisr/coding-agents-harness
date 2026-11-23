import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, alice, sampleCatalog } from '../helpers.js';

async function placed() {
  const gateway = new FakeGateway();
  const store = new OrderStore(sampleCatalog(), gateway);
  const cart = new Cart();
  cart.add('MUG', 1);
  const order = await store.place(alice, cart, null, new Date('2026-09-01T00:00:00Z'));
  return { gateway, store, order };
}

describe('spec still met: refunds recorded after the gateway', () => {
  it('shows nothing refunded while the call is in flight', async () => {
    const { gateway, store, order } = await placed();
    gateway.delayMs = 20;
    const pending = store.refund(ada, order.id, 500);
    expect(store.get(ada, order.id)?.refundedCents).toBe(0);
    await pending;
    expect(store.get(ada, order.id)?.refundedCents).toBe(500);
  });
  it('records nothing when the gateway fails, and the amount can be refunded again', async () => {
    const { gateway, store, order } = await placed();
    gateway.failNext = true;
    await expect(store.refund(ada, order.id, order.totalCents)).rejects.toThrow();
    expect(store.get(ada, order.id)?.refundedCents).toBe(0);
    await store.refund(ada, order.id, order.totalCents);
    expect(store.get(ada, order.id)?.refundedCents).toBe(order.totalCents);
  });
});
