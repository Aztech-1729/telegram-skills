# Public Telegram skill comparison — 2026-10-04

Some public packs have deeper coverage in particular areas. This repository has
broader bundled language examples and a substantial validation/maintenance setup;
that does not make it universally better. Choose by the requested task, actual
resources and verification evidence rather than star counts or skill counts.

## Method and boundaries

Discovery used web search, GitHub repository/code search and skill-directory
results for Telegram bots, `SKILL.md`, keyboards, grammY, Mini Apps, testing and
agent skills. The comparison below uses original repositories at immutable
commits, not directory descriptions alone. Selected entrypoints, resources,
manifests or tests supporting each row were inspected. Peer code was not
installed or executed, and peer text/code/assets were not copied into this pack.

This is a reproducible sample, not every website or a complete audit of each
peer. A README claim, existing test file, successful build and measured live
behavior are separate evidence. No controlled agent-success benchmark was run,
so no overall winner, percentage improvement or quality multiplier is claimed.

The starting version of this repository was
`5d0c1d63b7a7abe5a70330a5956a23a06abb687d` (21 skills). The follow-up resources
described below accompany native plugin patch **1.1.1**; publication and validation
status are established by their PR/run, not by this comparison document.

## Capabilities found in primary sources

| Peer and exact snapshot | Useful strength observed | This pack's response / remaining difference |
|---|---|---|
| [hlibsuslov/telegram-bot-ui](https://github.com/hlibsuslov/telegram-bot-ui/tree/0fc82a72d590410f485b10e991edfd594868d45b) | Its [keyboard validator](https://github.com/hlibsuslov/telegram-bot-ui/blob/0fc82a72d590410f485b10e991edfd594868d45b/scripts/validate_keyboard.py) handles inline/reply payloads and provides layout/label warnings; detailed native UI references are easy to select. | Added an original [inline-markup validator](../telegram-bot-keyboards-ui/scripts/validate_keyboard.py) against Bot API 10.3 with explicit context checks and tests. Reply-keyboard validation and broad label/layout heuristics remain a peer strength. |
| [pewpewgogo/telegram-bot-skill](https://github.com/pewpewgogo/telegram-bot-skill/tree/04c4fbd1f47c732d97a2f66d961c0dc5e40f126f) | Twelve focused grammY-oriented skills include a dedicated [conversation guide](https://github.com/pewpewgogo/telegram-bot-skill/blob/04c4fbd1f47c732d97a2f66d961c0dc5e40f126f/skills/telegram-bot-conversations/SKILL.md), plus sessions, scaling, testing and routing. Its inspected CI validates skill structure. | Added [dialog/replay guidance](../telegram-bot-javascript/references/conversations.md) and a real-plugin feedback factory with five offline behavior tests. The general JavaScript skill also retains Telegraf; dedicated grammY topic entrypoints can be quicker for an exclusively grammY project. |
| [yaniv-golan/telegram-webapps-skill](https://github.com/yaniv-golan/telegram-webapps-skill/tree/f82df26d58e47e9ff7825b6332c70fbcf14d71de) | A bundled browser SDK mock, boilerplate, multiple-language auth helpers and a substantial [developer setup guide](https://github.com/yaniv-golan/telegram-webapps-skill/blob/f82df26d58e47e9ff7825b6332c70fbcf14d71de/.agents/skills/telegram-webapps/references/developer-setup.md) give more local prototyping scaffolding. | Our runnable todo uses a Python backend and vanilla frontend; its DOM/auth tests cover selected invariants. A reusable visual SDK mock and Node/Go backend adapters are genuine remaining gaps. Mock identity and payment stubs do not establish authenticated or paid behavior. |
| [Rithprohos/telegram-mini-app-skills](https://github.com/Rithprohos/telegram-mini-app-skills/tree/ae8cfc1e34894b7a28ba784c6e5de7ca265be40e) | Its [skill](https://github.com/Rithprohos/telegram-mini-app-skills/blob/ae8cfc1e34894b7a28ba784c6e5de7ca265be40e/SKILL.md) explicitly includes React/Next, Vue/Nuxt and Svelte/SvelteKit integration recipes. | We provide SDK lifecycle/design guidance and a vanilla example, not runnable projects for those frontends. Broader snippet coverage is useful, but the inspected fragments were not built; framework syntax, SSR and listener cleanup still need verification. |
| [nzhulikov/telegram-bot-skills](https://github.com/nzhulikov/telegram-bot-skills/tree/2dee91da355260eafecea8162438090b619d64bc) | Twenty-one API-topic entrypoints include a separate [games skill](https://github.com/nzhulikov/telegram-bot-skills/blob/2dee91da355260eafecea8162438090b619d64bc/skills/telegram-bot-api/18-games/SKILL.md), making narrow API-family discovery direct. | We combine framework specialists with feature skills and a capability map. Games, Passport and some other families have official lookup routes, not dedicated runnable specialists. More entrypoints do not imply more tested implementations. |
| [kirniy/telegram-bot-api-docs-skill](https://github.com/kirniy/telegram-bot-api-docs-skill/tree/aa94c97f4f016c2456ef7ad03444906664c96b6c) | A compact API-reference skill includes a latest-version checker and four [parser regression tests](https://github.com/kirniy/telegram-bot-api-docs-skill/blob/aa94c97f4f016c2456ef7ad03444906664c96b6c/tests/test_check_latest.py). | Our monitor checks normalized official sources and package releases and preserves unresolved reviews. This is a different maintenance scope; neither a parsed version nor a changed hash proves semantic compatibility. |

Several peers include checked-in licenses. This repository still has no license
file, which is a distribution-policy gap for the maintainer to resolve. The
Rithprohos README links MIT, but the inspected snapshot did not contain that
license file; a badge alone is not proof of a repository's license contents.

## Adjacent tools serve another task

Projects such as
[hec-ovi/telegram-bot-skill](https://github.com/hec-ovi/telegram-bot-skill/tree/4e2e196b1984d6652fc78b6d508184094a428f78)
and [teamily-ai/telegram-bot-skill](https://github.com/teamily-ai/telegram-bot-skill/tree/11b35a38d584ff7d7a2ff15cbae2a347960e316e)
bundle agent-bridge or Telegram operation code. Live messaging, daemon operation
or account access can be useful capabilities, but they are a different purpose
from portable instructions for developing a bot. They were discovery/scope
references, not fully audited or executed competitors. Installing this pack does
not grant Telegram access or deploy a bridge.

## Changes justified by this follow-up

- The keyboard helper counts action-field presence, accepts current disabled
  actions, checks context/type/bounds, rejects duplicate JSON fields and reports
  errors without echoing payload values. Its eleven new tests join existing UI tests.
  Independent review also caught and fixed chosen-chat payloads with no enabled
  chat type, verified against the official server and its pinned TDLib source.
- The grammY example tests actual replay through conversations 2.1.1, confirmation,
  cancellation, account denial, chat isolation and ambiguous-save recovery.
  Documentation identifies cached permission and crash/durable-idempotency limits.
- A separate audit finding fixed reminder deadlines calculated from batch-start
  time. Slow-batch and fractional-clock tests preserve the full retry delay after
  the failure arrives.
- The full framework reread reproduced aiogram state loss/advance after failed
  prompts. Three real-FSM failure/retry regressions now retain the previous state
  and answers until step, restart or cancellation replies succeed. The guide
  states the remaining send/storage crash and uncertainty boundaries.
- README routing and validation evidence distinguish current results from older
  historical runs. Both native plugin versions advance together to 1.1.1.

## Remaining work and audit status

The [second full audit](AUDIT.md) reread all **221 source files** across the 21
skill folders and root tooling/configuration. Complete inventories cover 102
framework files, 74 feature files, 19 root Python tools/tests and 26 root
configuration/documentation files. The reproduced reminder and aiogram defects
were fixed and tested. Root configuration and maintenance-code reviews found no
additional material issue. This does not make the selected peer sample exhaustive
or certify every platform feature. Publication still requires independent review
of the exact final diff and native validation under the
[maintenance runbook](AGENT_MAINTENANCE.md); [PR #12](https://github.com/Aztech-1729/telegram-skills/pull/12)
records the actual result.

The remaining product gaps are a visual development SDK mock, tested frontend and
backend adapters, selected API-family implementations and an explicit license.
Target-client screen-reader, rendering, permission, payment and deployed receiver
acceptance also remain live checks. Add focused examples with genuine tests when
those tasks are implemented; do not turn untested snippets into readiness claims.
