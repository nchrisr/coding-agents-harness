# Order sharing

**Tier:** 3: it changes who can see an order.
**Systems:** sign-in-and-access (teach-me), state-and-timing (keep-me-posted)
**Why:** customers buying gifts want a partner to see the order and track it.

## Decisions
### Who can share
- **Chosen:** only the order's own customer. A user an order was shared with can't share it further,
  and staff can't share customers' orders.

### What sharing gives
- **Chosen:** the shared user can view the order (`get`, `listFor`), and nothing else: no refunds,
  no sharing.

### Sharing with yourself
- **Options:** throw an error; ignore it.
- **Chosen:** ignore it: return the order unchanged, with no error. The share box in the app lists
  everyone in the household, owner included, and selecting all must not fail.

### Sharing twice with the same person
- **Chosen:** ignore the repeat; the user is listed once.

## Changes
- `src/orders.ts`: `sharedWith` on `Order`; `OrderStore.share`.
- `src/access.ts`: `canViewOrder` lets shared users view.

## Testing
A shared user sees the order; a stranger doesn't; a shared user can't refund.
