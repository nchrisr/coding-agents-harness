# Record refunds after the gateway confirms

**Tier:** 3: refunds move money.
**Systems:** state-and-timing (keep-me-posted), money-and-numbers (teach-me)
**Why:** `refund` adds to `refundedCents` before calling the gateway, and takes it back if the call
fails. A support agent looking at the order during the call sees a refund that may never happen, and
has told customers "it's refunded" when the gateway then failed.

## Decisions
### When a refund shows on the order
- **Chosen:** `refundedCents` changes only after the gateway confirms. While the call is in flight,
  the order shows the old amount.

### The limit
- **Chosen:** unchanged: the total refunded never exceeds what was paid.

## Changes
- `src/orders.ts`: `refund` calls the gateway first and records after it succeeds; the failure path
  no longer needs to undo anything.

## Testing
The existing refund tests, plus: `refundedCents` is unchanged while the gateway call is in flight.
