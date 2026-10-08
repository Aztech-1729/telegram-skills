# Rendering, catalog and report patterns

## Ordinary formatting

Choose HTML for a constrained formatting vocabulary, MarkdownV2 when its escaping is intentional, or explicit entities for precise ranges. Escape user-controlled HTML with `html.escape`; escape MarkdownV2 according to the context (normal text, code, URL). Avoid processing user markup as trusted templates. Entity offsets/lengths are measured in UTF-16 code units; splitting a Python string by characters does not automatically preserve entity ranges.

Use bold for labels, code for identifiers or compact numeric data, consistent limited emoji for navigation/status, expandable quotations for optional detail, and current date-time entities for localized times. Preserve accessible plain text and useful fallback emoji for custom emoji. Refer to [keyboards UI](../../telegram-bot-keyboards-ui/SKILL.md) for current button styles and entity fields.

Regular formatting is not Rich HTML. Do not send GFM headings/tables through ordinary `sendMessage` and expect document-like rendering. Rich Message input selects one representation: `html`, `markdown`, or `blocks`; choose it based on the source material. Media references and block type structure must follow the current API schema. See [InputRichMessage](https://core.telegram.org/bots/api#inputrichmessage).

## A catalog is a view of application state

Store product ID, display label, price/currency, availability and fulfillment policy as separate fields. Rendering reads that state; it does not decide authorization. Use server-generated product identifiers, bounded page numbers and per-user cart ownership. Never treat a callback's quoted price as authoritative.

An interaction sequence can be:

```text
catalog page -> product details -> current checkout quote -> payment event
                                                -> verified order -> fulfillment
```

The payment service checks price, amount, currency, user, inventory and payload binding. A download button looks up the user's completed entitlement. A successful payment handler records a unique charge before delivery; retry-safe delivery uses the application's order ledger. Refund/access revocation is a separate flow.

## Original HTML catalog renderer

This renderer creates only a view; it has no payment or delivery claim:

```python
from html import escape

def render_catalog(products, page=0, page_size=6):
    if page_size < 1 or page < 0:
        raise ValueError("Invalid pagination")
    rows = products[page * page_size:(page + 1) * page_size]
    lines = ["<b>Catalog</b>", ""]
    for product in rows:
        label = escape(str(product["label"]))
        price = escape(str(product["display_price"]))
        lines.append(f"• <b>{label}</b> — <code>{price}</code>")
    return "\n".join(lines) if rows else "No products on this page."
```

Build callback buttons with the framework skill; validate a page against the current total and check product/order ownership in the handler. On an expired view, reopen a fresh authorized catalog instead of trusting old payloads.

## Reports and layouts

| Content | Useful structure | Design check |
|---|---|---|
| Short outcome | Result, affected object, next action | Success describes a confirmed operation, not a queued attempt |
| Catalog detail | Title, relevant attributes, price/currency, availability, action | Price is current; button references the authorized object |
| Report | Summary, period/timezone, units, values, detail/export | Reading order survives without a visual table |
| Warning/error | Consequence, retained state, recovery | No secrets/internal trace; color alone isn't the explanation |
| Generated answer | Partial status, final result, relevant sources | Don't present invented data or a draft as verified final output |

Use [the UX guide](../../telegram-bot-ux/references/guide.md) for primary/secondary,
positive/destructive action roles. Rich buttons use their own schema; its `link`
style doesn't apply to ordinary inline buttons. Meaningful labels, text status and
linear reading order serve users who cannot rely on color or visual alignment.

Group related metrics; show the reporting period/timezone and define ambiguous units. Include the data's timestamp when relevant. Use a short summary followed by detail, rather than an unbounded formatted wall. For rich tables, map known columns and escape each cell; do not interpolate arbitrary HTML into structural tags. Attach documents when dense content is better read outside chat.

Separate “generation in progress,” “completed,” and “delivery failed.” Do not represent partial data as a final result. Images/media captions need their own size/format checks; albums and inline rich media are different payload shapes. Decide whether a link preview improves the layout and verify it across clients.

## UI completion checklist

Consistent navigation, a clear return path, command registration, meaningful empty/error states, bounded pagination, localized text where needed, current stock/price, escaped values, and server-side callback authorization. A visually polished storefront still needs the persistence, checkout and delivery checks from the other skills.

When ordinary text exceeds its method's limit, split at deliberate content
boundaries or attach a document. Preserve complete entities/tags and avoid
breaking a grapheme merely to fit a byte count. Empty plain drafts display a
temporary “Thinking…” placeholder. Rich drafts can use `<tg-thinking>` or
`InputRichBlockThinking` for a visible progress placeholder; this represents UI
status, not a transcript of model reasoning. See [streaming replies](https://core.telegram.org/bots/features#streaming-replies).
Stop flags in the helper must be actual booleans, not strings such
as `"false"`. The builder validates representation and identity shape, not every
rich block, media entitlement or rendering limit. Consult the exact method/schema
before sending a new block type.
