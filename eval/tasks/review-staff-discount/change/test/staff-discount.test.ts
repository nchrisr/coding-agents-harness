import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../src/cart.js';
import { alice, sam, sampleCatalog } from './helpers.js';

function tee(): Cart {
  const cart = new Cart();
  cart.add('TEE', 1);
  return cart;
}

describe('staff discount', () => {
  it('gives staff 15% off', () => {
    const totals = cartTotals(sampleCatalog(), tee(), null, sam);
    expect(totals.discountCents).toBe(299);
  });

  it('gives customers nothing', () => {
    expect(cartTotals(sampleCatalog(), tee(), null, alice).discountCents).toBe(0);
  });

  it('uses a bigger code instead of the staff discount', () => {
    const code = { code: 'HALF', kind: 'percent' as const, percent: 50 };
    expect(cartTotals(sampleCatalog(), tee(), code, sam).discountCents).toBe(1000);
  });
});
