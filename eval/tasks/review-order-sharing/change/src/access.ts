import { type Order } from './orders.js';
import { type User } from './users.js';

/**
 * Customers see their own orders and orders shared with them; staff and admins see every order.
 */
export function canViewOrder(user: User, order: Order): boolean {
  if (user.role === 'staff' || user.role === 'admin') {
    return true;
  }
  return order.customerId === user.id || order.sharedWith.includes(user.id);
}

/** Only admins refund. */
export function canRefund(user: User, _order: Order): boolean {
  return user.role === 'admin';
}
