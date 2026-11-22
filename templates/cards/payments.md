---
name: payments
title: Payments
involvement: teach-me
owns:
  - '<billing, checkout, webhook code>'
watch:
  - '(charges|paymentIntents|refunds)\.create\('
  - 'constructEvent\(|verify\w*Webhook\('
---

# Payments

**Involvement:** Teach me. A charge taken twice, or not at all, costs money and trust.
**The question:** can this charge, refund or credit happen twice, or not at all?

## Invariants (always true)
- Every charge has an idempotency key; a retry never charges twice.
- The payment provider's webhook is verified before it's trusted.
- Prices come from the server, never from the browser.

## Tripwires (changes that pull you in, even from a trusted area)
- <adapt to the project>

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** <tests, lint rules, guard tests>
- **Reviewer:** can this charge, refund or credit happen twice, or not at all?

## Briefing
<what the owner gets>
