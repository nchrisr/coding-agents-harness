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
  /** Users the customer shared the order with. They can view it, nothing more. */
  sharedWith: string[];
}

/** Places orders, takes payment and refunds. Orders are kept in memory. */
export class OrderStore {
  private readonly orders = new Map<string, Order>();
  private nextId = 1;

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
        sharedWith: [],
      };
      this.nextId += 1;
      this.orders.set(order.id, order);
      return order;
    } catch (error) {
      for (const line of taken) {
        this.catalog.putBack(line.sku, line.quantity);
      }
      throw error;
    }
  }

  /** The order if this user may see it; null when it doesn't exist or they may not. */
  get(user: User, orderId: string): Order | null {
    const order = this.orders.get(orderId);
    if (order === undefined || !canViewOrder(user, order)) {
      return null;
    }
    return order;
  }

  /**
   * Shares an order with another user, who can then view it. Sharing with yourself, or with someone
   * already on the list, changes nothing (docs/specs/2026-11-21_order-sharing.md).
   */
  share(owner: User, orderId: string, withUserId: string): Order {
    const order = this.orders.get(orderId);
    if (order === undefined || order.customerId !== owner.id) {
      throw new Error(`no order ${orderId} that you can share`);
    }
    if (withUserId === owner.id) {
      return order;
    }
    if (!order.sharedWith.includes(withUserId)) {
      order.sharedWith.push(withUserId);
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
