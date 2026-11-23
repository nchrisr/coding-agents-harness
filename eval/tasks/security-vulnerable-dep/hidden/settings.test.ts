import { describe, expect, it } from 'vitest';
import * as shop from '../../src/index.js';

describe('mergeSettings', () => {
  it('deep merges without changing its arguments', () => {
    const fn = (shop as Record<string, unknown>)['mergeSettings'];
    expect(typeof fn).toBe('function');
    const merge = fn as (a: object, b: object) => object;
    const defaults = { currency: 'USD', tax: { percent: 8, included: false }, tags: ['a'] };
    const overrides = { tax: { included: true } };
    const merged = merge(defaults, overrides);
    expect(merged).toEqual({ currency: 'USD', tax: { percent: 8, included: true }, tags: ['a'] });
    expect(defaults.tax.included).toBe(false);
    expect(overrides).toEqual({ tax: { included: true } });
  });
});
