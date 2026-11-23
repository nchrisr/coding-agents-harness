import { describe, expect, it } from 'vitest';
import { Cart, cartTotals } from '../src/cart.js';
import { DiscountBook } from '../src/discounts.js';
import { sampleCatalog } from './helpers.js';

describe('cartTotals', () => {
  it('adds lines and tax', () => {
    const cart = new Cart();
    cart.add('MUG', 2);
    cart.add('PEN', 1);
    const totals = cartTotals(sampleCatalog(), cart, null);
    expect(totals.subtotalCents).toBe(2699);
    expect(totals.discountCents).toBe(0);
    expect(totals.taxCents).toBe(216);
    expect(totals.totalCents).toBe(2915);
  });

  it('merges the same SKU', () => {
    const cart = new Cart();
    cart.add('PEN', 1);
    cart.add('PEN', 2);
    expect(cart.lines()).toEqual([{ sku: 'PEN', quantity: 3 }]);
  });

  it('rejects bad quantities', () => {
    const cart = new Cart();
    expect(() => cart.add('PEN', 0)).toThrow();
    expect(() => cart.add('PEN', 1.5)).toThrow();
  });

  it('applies a percent code before tax', () => {
    const book = new DiscountBook();
    book.add({ code: 'TEN', kind: 'percent', percent: 10 });
    const cart = new Cart();
    cart.add('TEE', 1);
    const totals = cartTotals(sampleCatalog(), cart, book.find('ten'));
    expect(totals.discountCents).toBe(200);
    expect(totals.taxCents).toBe(144);
    expect(totals.totalCents).toBe(1943);
  });

  it('never discounts below zero, and respects minimum spend', () => {
    const book = new DiscountBook();
    book.add({ code: 'BIG', kind: 'fixed', amountCents: 5000 });
    book.add({ code: 'MIN', kind: 'fixed', amountCents: 100, minSubtotalCents: 1000 });
    const cart = new Cart();
    cart.add('PEN', 1);
    expect(cartTotals(sampleCatalog(), cart, book.find('BIG')).totalCents).toBe(0);
    expect(cartTotals(sampleCatalog(), cart, book.find('MIN')).discountCents).toBe(0);
  });

  it('throws on an unknown SKU', () => {
    const cart = new Cart();
    cart.add('NOPE', 1);
    expect(() => cartTotals(sampleCatalog(), cart, null)).toThrow(/unknown SKU/);
  });
});
