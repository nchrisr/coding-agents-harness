import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../../src/cart.js';
import { sam, sampleCatalog } from '../helpers.js';

describe('decoy: the staff discount rounds down, as the spec asks', () => {
  it('takes 299 off 1999, not 300', () => {
    const cart = new Cart();
    cart.add('TEE', 1);
    const totals = cartTotals(sampleCatalog(), cart, null, sam);
    expect(totals.discountCents).toBe(299);
    expect(totals.totalCents).toBe(1836);
  });
  it('rounds 15% of 199 down to 29', () => {
    const cart = new Cart();
    cart.add('PEN', 1);
    expect(cartTotals(sampleCatalog(), cart, null, sam).discountCents).toBe(29);
  });
});
