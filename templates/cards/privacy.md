---
name: privacy
title: Privacy
involvement: teach-me
owns:
  - "<profile, email, notification, logging code>"
watch:
  - "email"
  - "phone"
  - "address|console\.log|logger"
---

# Privacy

**Involvement:** Teach me. Personal data reaching the wrong place can't be undone.
**The question:** where does personal data go, and who can read it there?

## Invariants (always true)
- Personal data is read only where needed and never logged.
- Nothing personal goes in a URL, a push notification or an analytics event.
- Email and notifications go to verified addresses only.

## Tripwires (changes that pull you in, even from a trusted area)
- <adapt to the project>

## How it breaks
- <the project's own incidents>

## Checks
- **Programs:** <tests, lint rules, guard tests>
- **Reviewer:** where does personal data go, and who can read it there?

## Briefing
<what the owner gets>
