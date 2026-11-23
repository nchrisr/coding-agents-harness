import { type Cents } from './money.js';

/** The outside payment provider. Tests pass a fake. */
export interface PaymentGateway {
  charge(customerId: string, amountCents: Cents): Promise<string>;
  refund(chargeId: string, amountCents: Cents): Promise<void>;
}
