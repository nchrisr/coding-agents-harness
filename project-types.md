# Project types

Setup asks which one a project is. The type only sets the dial's defaults; each card can override.
In a public repository, learning settings can stay private: the committed cards use only teach-me,
keep-me-posted and trust, and the type and coach overrides live in the project's private notes file.

| | Product (taxi) | Learning (driving school) |
|---|---|---|
| Goal | Get there safely | The owner learns the system |
| Who drives | The builder agent | The owner, on the parts they choose |
| Critical systems | Teach me | Teach me |
| Everything else | Keep me posted or Trust | Teach me, or I build it, you coach |
| The agent writes | The change | Scaffolding, tests, the boring parts; explains concepts |
| Done means | Checks pass, reviewed, demoed | The owner can explain how it works |

## The dial

| Setting | What the owner gets |
|---|---|
| **Teach me** | Before merge, a briefing: the decisions made, how data flows through, and 2–3 realistic ways it could break. Specs walked through one decision at a time. |
| **Keep me posted** | No wait. A note in the change's summary: what changed and anything odd noticed. |
| **Trust** | The demo only. |
| **I build it, you coach** | The agent sets up scaffolding and tests and leaves the named part to the owner. It explains, hints and reviews; it doesn't write that part unless asked. |

**Tripwires** pull a change up to *Teach me* from any setting. Each card lists its own.
