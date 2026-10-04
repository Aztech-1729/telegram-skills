# Skill audit — 2026-10-04

The complete pre-audit pack of **18 skills and 137 skill resources** was read,
including instructions, references, starters, tests and dependency manifests.
Ignored downloads/build outputs were excluded. The pack now contains **21 skills**
with three new specialists: [bot UX](../telegram-bot-ux/SKILL.md),
[Mini App design](../telegram-bot-miniapp-design/SKILL.md) and
[accessibility](../telegram-bot-accessibility/SKILL.md).

The audit checked actual implementation behavior and relevant current primary
documentation. It does not claim to have reviewed every upstream page, tested
every Telegram method or measured an arbitrary quality multiplier. Source
observations and substantive review remain separate.

## Concrete corrections

| Area | Defect / gap addressed |
|---|---|
| PTB | Retain conversation state across a failed final reply; recover stale callbacks |
| aiogram | Include bot identity in optional shared Redis keys; cover invalid/stale actions |
| Telethon / gotd | Verify the identity associated with a reused session and keep session/auth boundaries explicit |
| Go HTTP | Correct the SDK webhook's acknowledgment/body-limit/durability assumptions; exercise the actual receiver locally |
| JavaScript | Add topic, inline/stale callback and non-message-update behavior checks |
| Java | Close the polling executor explicitly; check received versus send-model direct-message topic ranges |
| .NET / PHP / Rust | Preserve topic context and add offline payload/dispatch checks with explicit wrapper boundaries |
| Fundamentals | Add HTTP capability paths, update-subscription defaults, retention and chat-ID migration decisions |
| Recipes | Isolate permanent reminder failures, persist bounded retries/rate-limit cooldown, enforce owner/topic boundaries, recover stale quiz actions and check downloader outcomes |
| Payments | Validate refund-event identity/currency/amount before reversing credit; clarify recurring and paid-media integration |
| Advanced operations | Distinguish Forbidden causes, validate outbox inputs and expose privacy-safe queue state; clarify receiver acknowledgment versus handler completion |
| Native chat UI | Replace red Cancel examples with neutral dismissal; document semantic color roles and SDK/client distinctions |
| Mini App frontend | Block duplicate in-flight writes, preserve failed input, clear/lock expired sessions, explain uncertain outcomes, restore deleted-item focus and use all four content insets |
| Rich messaging | Reject string/numeric stop flags rather than silently changing generation policy; improve content hierarchy and builder limits |

Read each family's source register and troubleshooting reference for its exact
baseline and integration limits. A server feature, library type and client UI are
different compatibility checks.

## UI/UX coverage

- **Bot UX:** task/surface selection, onboarding and returning users, navigation,
  state contracts, button hierarchy, semantic colors, destructive confirmation,
  permission denial, checkout truth, microcopy and stale/failed recovery.
- **Mini App design:** theme token pairs, measured contrast, primary/secondary/
  danger components, responsive type/spacing, all four content safe areas, forms,
  lists, dialogs and native button/event lifecycle. Includes extractable CSS.
- **Accessibility:** native-client versus web responsibilities, meaningful labels,
  keyboard/focus behavior, status announcements, localization/RTL, reduced motion,
  AA versus AAA criteria and actual acceptance scenarios. Includes an opaque-sRGB
  contrast checker with tests.

Blue primary, green success and red danger are native Telegram semantic styles;
neutral dismissal and peer choices usually omit style. Exact RGB belongs to the
Mini App surface, not ordinary bot keyboards. These are application design
recommendations where stated, not invented Telegram limits. WCAG criteria apply
to app-controlled web content; native Telegram focus/rendering remains client-controlled.

## Verification and distribution

The required workflow checks the complete pack, native plugin metadata and the
real installer in both all-agent and selected-agent copy modes. The new skills
are bundled in both `telegram@aztech` native manifests as version **1.1.0**.
The same one-command install now retrieves the full 21-skill catalog.

Behavior checks cover framework routing/recovery, storage/payment/outbox
invariants, Mini App controls/session expiry and contrast calculations. Java,
.NET, PHP, Rust and Go checks run in the hosted workflow as well as available
local toolchains. Local fake transports/DOMs establish tested invariants, not
universal client appearance. The [validation workflow](../.github/workflows/validate.yml)
records the exact current results and toolchains.

Daily source monitoring also tracks the new primary W3C sources under explicit
approved documentation paths. Changed/unavailable sources stay visible until
review; a successful fetch is not compatibility certification. The daily
maintenance agent uses the existing review and protected-merge boundaries.

## Remaining live acceptance

Exercise target Telegram clients, custom themes, narrow/RTL/large-text layouts,
screen readers and native permission/navigation behavior. Test actual webhook
deployment and authorized payment/renewal/refund flows in the intended development
environment. Offline checks and read-only bot authentication do not prove live
delivery, accessibility compliance or production readiness.
