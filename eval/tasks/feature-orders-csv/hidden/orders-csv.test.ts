import { describe, expect, it } from 'vitest';
import { Cart } from '../../src/cart.js';
import { Catalog } from '../../src/catalog.js';
import * as shop from '../../src/index.js';
import { OrderStore } from '../../src/orders.js';
import { FakeGateway, ada, alice, bob, sam, sampleCatalog } from '../helpers.js';

const HEADER = 'order_id,customer_id,placed_at,items,total,refunded';

function exporter(): (store: OrderStore, user: typeof alice) => string {
  const fn = (shop as Record<string, unknown>)['exportOrdersCsv'];
  if (typeof fn !== 'function') {
    throw new Error('exportOrdersCsv is not exported from src/index.ts');
  }
  return fn as (store: OrderStore, user: typeof alice) => string;
}

async function twoCustomers() {
  const store = new OrderStore(sampleCatalog(), new FakeGateway());
  const a = new Cart();
  a.add('MUG', 2);
  a.add('PEN', 1);
  const first = await store.place(alice, a, null, new Date('2026-06-01T08:00:00Z'));
  const b = new Cart();
  b.add('TEE', 1);
  await store.place(bob, b, null, new Date('2026-06-02T09:15:30Z'));
  return { store, first };
}

describe('exportOrdersCsv', () => {
  it('gives only the header when there are no orders', () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    expect(exporter()(store, alice)).toBe(`${HEADER}\n`);
  });

  it('writes one row per order the user may see', async () => {
    const { store } = await twoCustomers();
    expect(exporter()(store, alice)).toBe(
      `${HEADER}\norder-1,u-alice,2026-06-01T08:00:00.000Z,MUG x 2; PEN x 1,29.15,0.00\n`,
    );
  });

  it('shows staff and admins every order, oldest first', async () => {
    const { store } = await twoCustomers();
    const rows = exporter()(store, sam).split('\n');
    expect(rows[0]).toBe(HEADER);
    expect(rows[1]?.startsWith('order-1,u-alice,')).toBe(true);
    expect(rows[2]).toBe('order-2,u-bob,2026-06-02T09:15:30.000Z,TEE x 1,21.59,0.00');
    expect(rows).toHaveLength(4);
    expect(exporter()(store, ada)).toBe(exporter()(store, sam));
  });

  it('shows refunded amounts', async () => {
    const { store, first } = await twoCustomers();
    await store.refund(ada, first.id, 1005);
    expect(exporter()(store, alice)).toContain(',29.15,10.05\n');
  });

  it('quotes fields with commas, quotes and newlines', async () => {
    const catalog = new Catalog();
    catalog.add({ sku: 'A,B', name: 'Comma', priceCents: 100, stock: 9 });
    catalog.add({ sku: 'Q"T', name: 'Quote', priceCents: 100, stock: 9 });
    const store = new OrderStore(catalog, new FakeGateway());
    const cart = new Cart();
    cart.add('A,B', 1);
    cart.add('Q"T', 2);
    await store.place(alice, cart, null, new Date('2026-06-03T00:00:00Z'));
    expect(exporter()(store, alice)).toBe(
      `${HEADER}\norder-1,u-alice,2026-06-03T00:00:00.000Z,"A,B x 1; Q""T x 2",3.24,0.00\n`,
    );
  });

  it('quotes a customer id with a newline', async () => {
    const store = new OrderStore(sampleCatalog(), new FakeGateway());
    const odd = { id: 'u-odd\nname', name: 'Odd', role: 'customer' as const };
    const cart = new Cart();
    cart.add('PEN', 1);
    await store.place(odd, cart, null, new Date('2026-06-04T00:00:00Z'));
    expect(exporter()(store, sam)).toContain('order-1,"u-odd\nname",');
  });
});
