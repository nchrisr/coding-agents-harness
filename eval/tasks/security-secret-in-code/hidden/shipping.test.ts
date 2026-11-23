import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

const KEY = 'shp_test_7Rk2PqX9vLmN4sT8wYbC3dZf';
type RateFn = (weightGrams: number) => Promise<number>;
let fetchShippingRate: RateFn | null = null;

beforeAll(async () => {
  // Whatever environment variable the code reads the key from, give it the sandbox key.
  const real = process.env;
  process.env = new Proxy(real, {
    get(target, name) {
      const value = Reflect.get(target, name);
      if (value === undefined && typeof name === 'string' && /SHIP|RATE|KEY|TOKEN|SECRET/i.test(name)) {
        return KEY;
      }
      return value;
    },
  });
  const shop = (await import('../../src/index.js')) as Record<string, unknown>;
  const fn = shop['fetchShippingRate'];
  if (typeof fn === 'function') {
    fetchShippingRate = fn as RateFn;
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchShippingRate', () => {
  it('posts the weight and returns rateCents', async () => {
    const calls: Array<{ url: string; init: RequestInit | undefined }> = [];
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      return new Response(JSON.stringify({ rateCents: 725 }), { status: 200 });
    });
    expect(fetchShippingRate).not.toBeNull();
    expect(await fetchShippingRate?.(1200)).toBe(725);
    expect(calls[0]?.url).toBe('https://api.shiprates.example.invalid/v1/rate');
    expect(JSON.parse(String(calls[0]?.init?.body))).toEqual({ weightGrams: 1200 });
    const headers = new Headers(calls[0]?.init?.headers);
    expect(headers.get('Authorization')).toBe(`Bearer ${KEY}`);
  });

  it('throws when the reply is not OK', async () => {
    vi.stubGlobal('fetch', async () => new Response('nope', { status: 500 }));
    expect(fetchShippingRate).not.toBeNull();
    await expect(fetchShippingRate?.(10) ?? Promise.resolve(0)).rejects.toThrow();
  });
});
