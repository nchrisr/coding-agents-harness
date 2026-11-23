import { canRefund, canViewOrder } from './access.js';
import { type Cart, type CartLine, cartTotals } from './cart.js';
import { type Catalog } from './catalog.js';
import { type Discount } from './discounts.js';
import { type Cents, assertCents } from './money.js';
import { type PaymentGateway } from './payments.js';
import { type User } from './users.js';

export interface Order {
  id: string;
  customerId: string;
  lines: CartLine[];
  totalCents: Cents;
  refundedCents: Cents;
  chargeId: string;
  /** When the order was placed. */
  placedAt: Date;
}

/** Places orders, takes payment and refunds. Orders are kept in memory. */
export class OrderStore {
  private readonly orders = new Map<string, Order>();
  private nextId = 1;
  /** Uses per code (upper case), counting orders still waiting on the gateway. */
  private readonly uses = new Map<string, number>();

  constructor(
    private readonly catalog: Catalog,
    private readonly gateway: PaymentGateway,
  ) {}

  /**
   * Takes stock, charges the customer and records the order. If the charge fails, the stock goes
   * back and nothing is recorded.
   */
  async place(customer: User, cart: Cart, discount: Discount | null, now: Date): Promise<Order> {
    if (cart.isEmpty()) {
      throw new Error('cart is empty');
    }
    const lines = cart.lines();
    const totals = cartTotals(this.catalog, cart, discount);
    let codeKey: string | null = null;
    if (discount !== null) {
      if (discount.expiresAt !== undefined && now.getTime() >= discount.expiresAt.getTime()) {
        throw new Error(`discount ${discount.code} has expired`);
      }
      codeKey = discount.code.toUpperCase();
      const used = this.uses.get(codeKey) ?? 0;
      if (discount.maxUses !== undefined && used >= discount.maxUses) {
        throw new Error(`discount ${discount.code} has been used up`);
      }
      // Counted before the await, so an overlapping order sees this use.
      this.uses.set(codeKey, used + 1);
    }
    const taken: CartLine[] = [];
    try {
      for (const line of lines) {
        this.catalog.take(line.sku, line.quantity);
        taken.push(line);
      }
      const chargeId = await this.gateway.charge(customer.id, totals.totalCents);
      const order: Order = {
        id: `order-${this.nextId}`,
        customerId: customer.id,
        lines,
        totalCents: totals.totalCents,
        refundedCents: 0,
        chargeId,
        placedAt: now,
      };
      this.nextId += 1;
      this.orders.set(order.id, order);
      return order;
    } catch (error) {
      for (const line of taken) {
        this.catalog.putBack(line.sku, line.quantity);
      }
      if (codeKey !== null) {
        this.uses.set(codeKey, (this.uses.get(codeKey) ?? 1) - 1);
      }
      throw error;
    }
  }

  /** How many placed orders used a discount code. */
  timesUsed(code: string): number {
    return this.uses.get(code.toUpperCase()) ?? 0;
  }

  /** The order if this user may see it; null when it doesn't exist or they may not. */
  get(user: User, orderId: string): Order | null {
    const order = this.orders.get(orderId);
    if (order === undefined || !canViewOrder(user, order)) {
      return null;
    }
    return order;
  }

  /** Every order this user may see, oldest first. */
  listFor(user: User): Order[] {
    const visible: Order[] = [];
    for (const order of this.orders.values()) {
      if (canViewOrder(user, order)) {
        visible.push(order);
      }
    }
    return visible;
  }

  /** Refunds part or all of an order. The total refunded never exceeds what was paid. */
  async refund(user: User, orderId: string, amountCents: Cents): Promise<Order> {
    assertCents(amountCents, 'refund');
    if (amountCents <= 0) {
      throw new Error('refund must be more than zero');
    }
    const order = this.orders.get(orderId);
    if (order === undefined || !canRefund(user, order)) {
      throw new Error(`no order ${orderId} that you can refund`);
    }
    if (order.refundedCents + amountCents > order.totalCents) {
      throw new Error('refund is more than what is left on the order');
    }
    order.refundedCents += amountCents;
    try {
      await this.gateway.refund(order.chargeId, amountCents);
    } catch (error) {
      order.refundedCents -= amountCents;
      throw error;
    }
    return order;
  }
}
