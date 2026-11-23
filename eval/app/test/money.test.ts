import { describe, expect, it } from 'vitest';
import { formatCents, percentOf } from '../src/money.js';

describe('formatCents', () => {
  it('formats dollars and cents', () => {
    expect(formatCents(1234)).toBe('$12.34');
    expect(formatCents(5)).toBe('$0.05');
    expect(formatCents(0)).toBe('$0.00');
    expect(formatCents(-50)).toBe('-$0.50');
  });

  it('refuses fractions of a cent', () => {
    expect(() => formatCents(1.5)).toThrow();
  });
});

describe('percentOf', () => {
  it('rounds half up to whole cents', () => {
    expect(percentOf(1999, 10)).toBe(200);
    expect(percentOf(1000, 8)).toBe(80);
    expect(percentOf(5, 10)).toBe(1);
  });
});
