# Primary sources

Checked 2026-10-04; Bot API 10.3 (2026-08-24).

- [AI features for bots](https://core.telegram.org/api/bots/ai): generation, drafts, topics and stopping.
- [Bot API](https://core.telegram.org/bots/api#inputrichmessage): input representation and required payload parameters.
- [Bot features](https://core.telegram.org/bots/features#rich-messages): rendering and client-facing feature context.

The pack's renderers/payload builders are original examples; they do not certify SDK support or live client behavior.

Focused review **2026-10-08**: the complete Bot features page confirms that empty
plain drafts display “Thinking…” and rich drafts support a presentation
placeholder. The guide reflects that behavior; existing payload builders and
offline fixtures remain compatible. This review does not advance the earlier
Bot API/framework baseline or claim live client verification.
