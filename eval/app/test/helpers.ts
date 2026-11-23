import { Catalog } from '../src/catalog.js';
import { type Cents } from '../src/money.js';
import { type PaymentGateway } from '../src/payments.js';
import { type User } from '../src/users.js';

export const alice: User = { id: 'u-alice', name: 'Alice', role: 'customer' };
export const bob: User = { id: 'u-bob', name: 'Bob', role: 'customer' };
export const sam: User = { id: 'u-sam', name: 'Sam', role: 'staff' };
export const ada: User = { id: 'u-ada', name: 'Ada', role: 'admin' };

export function sampleCatalog(): Catalog {
  const catalog = new Catalog();
  catalog.add({ sku: 'MUG', name: 'Mug', priceCents: 1250, stock: 10 });
  catalog.add({ sku: 'TEE', name: 'T-shirt', priceCents: 1999, stock: 5 });
  catalog.add({ sku: 'PEN', name: 'Pen', priceCents: 199, stock: 100 });
  return catalog;
}

/** A payment gateway that records calls, and can be told to fail or to pause. */
export class FakeGateway implements PaymentGateway {
  charges: Array<{ customerId: string; amountCents: Cents }> = [];
  refunds: Array<{ chargeId: string; amountCents: Cents }> = [];
  failNext = false;
  /** Milliseconds each call waits, so overlapping calls can be tested. */
  delayMs = 0;

  async charge(customerId: string, amountCents: Cents): Promise<string> {
    await this.pause();
    if (this.failNext) {
      this.failNext = false;
      throw new Error('card declined');
    }
    this.charges.push({ customerId, amountCents });
    return `ch-${this.charges.length}`;
  }

  async refund(chargeId: string, amountCents: Cents): Promise<void> {
    await this.pause();
    if (this.failNext) {
      this.failNext = false;
      throw new Error('gateway down');
    }
    this.refunds.push({ chargeId, amountCents });
  }

  private async pause(): Promise<void> {
    if (this.delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delayMs));
    }
  }
}
