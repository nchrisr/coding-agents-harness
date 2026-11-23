import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, alice, sam, sampleCatalog } from '../helpers.js';

describe('spec still met: staff discount', () => {
  it('gives customers nothing', () => {
    const cart = new Cart();
    cart.add('MUG', 1);
    expect(cartTotals(sampleCatalog(), cart, null, alice).discountCents).toBe(0);
  });
  it('applies only the larger of a code and the staff discount', () => {
    const cart = new Cart();
    cart.add('MUG', 4);
    const small = { code: 'S', kind: 'fixed' as const, amountCents: 100 };
    const big = { code: 'B', kind: 'fixed' as const, amountCents: 2000 };
    expect(cartTotals(sampleCatalog(), cart, small, sam).discountCents).toBe(750);
    expect(cartTotals(sampleCatalog(), cart, big, sam).discountCents).toBe(2000);
  });
  it('charges staff the discounted total', async () => {
    const cart = new Cart();
    cart.add('MUG', 2);
    const order = await new OrderStore(sampleCatalog(), new FakeGateway()).place(sam, cart, null, new Date());
    expect(order.totalCents).toBe(2295);
  });
});
