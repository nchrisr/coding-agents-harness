import { describe, expect, it } from 'vitest';
import * as shop from '../../src/index.js';

describe('productSlug', () => {
  it('turns a product name into a slug', () => {
    const fn = (shop as Record<string, unknown>)['productSlug'];
    expect(typeof fn).toBe('function');
    const slug = fn as (p: { sku: string; name: string; priceCents: number; stock: number }) => string;
    expect(slug({ sku: 'M', name: 'Blue Mug (Large)', priceCents: 1, stock: 1 })).toBe('blue-mug-large');
    expect(slug({ sku: 'T', name: '  Tea & Biscuits  ', priceCents: 1, stock: 1 })).toBe('tea-biscuits');
  });
});
