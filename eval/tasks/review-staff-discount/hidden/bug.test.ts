import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../../src/cart.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, sampleCatalog } from '../helpers.js';

describe('planted bug: admins get no staff discount', () => {
  it('gives an admin no discount', () => {
    const cart = new Cart();
    cart.add('TEE', 1);
    expect(cartTotals(sampleCatalog(), cart, null, ada).discountCents).toBe(0);
  });
  it('charges an admin the full price', async () => {
    const gateway = new FakeGateway();
    const cart = new Cart();
    cart.add('MUG', 2);
    const order = await new OrderStore(sampleCatalog(), gateway).place(ada, cart, null, new Date());
    expect(order.totalCents).toBe(2700);
  });
});
