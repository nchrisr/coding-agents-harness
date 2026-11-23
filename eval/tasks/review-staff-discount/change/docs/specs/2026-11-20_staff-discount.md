# Staff discount

**Tier:** 3: it changes what customers are charged.
**Systems:** money-and-numbers (teach-me)
**Why:** staff buy from the shop and should get 15% off their own orders.

## Decisions
### Who gets it
- **Chosen:** users with the `staff` role only. Customers and admins get no staff discount (admins
  are the owners; the accountant treats their purchases separately).

### Rounding
- **Options:** round half up like other percentages; round down.
- **Chosen:** round **down** to whole cents. The accountant asked for this: the staff discount is a
  taxable benefit recorded in whole cents, and the shop never gives away part of a cent. So 15% of
  1999 is 299, not 300.

### With a discount code
- **Chosen:** only the larger of the staff discount and the code's discount applies. They never
  combine.

## Changes
- `src/money.ts`: `percentOfRoundedDown`.
- `src/cart.ts`: `cartTotals` takes the buyer and applies the staff discount.
- `src/orders.ts`: `place` passes the customer.

## Testing
Unit tests for a staff order, a customer order, and a staff order with a bigger code.
