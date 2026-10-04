# Accessibility responsibilities and checks

Reviewed 2026-10-04. WCAG criteria apply to web content under the app's control;
the recommendations for native Telegram messages borrow the same usable-design
principles without claiming control over Telegram's interface.

## Native bot content

Use informative message text and verb/object button labels. Avoid emoji-only or
color-only choices. Supply meaningful fallback emoji/text when using custom emoji.
Explain image/media content in adjacent text or captions when needed for the task;
don't assume a bot can assign HTML alt text to a native Telegram message.
Keep reports readable in linear order instead of relying on visual ASCII tables.
Offer concise summaries with optional detail and localized date/time context.

Test the actual native message and buttons in the target client with its screen
reader, text scaling and custom theme. Bots cannot set native ARIA attributes,
CSS focus styles or arbitrary keyboard button RGB. Those limitations should not
be used to excuse unclear labels or missing recovery actions.

## Mini App criteria and implementation

| Concern | Criterion / target | Application responsibility |
|---|---|---|
| Normal text | WCAG 1.4.3 AA: 4.5:1 contrast | Measure displayed foreground/background pairs |
| Large text | 1.4.3: 3:1; at least 18pt, or 14pt bold | Do not apply the large-text exemption to ordinary 16px labels |
| Required visual control/state cues | 1.4.11 AA: 3:1 against adjacent color, with exceptions | Borders, icons and selected/error states that carry meaning |
| Color alone | 1.4.1 A | Add labels, icons or structural cues |
| Pointer targets | 2.5.8 AA: 24 × 24 CSS px or sufficient spacing; listed exceptions apply | 44px controls are a useful comfort recommendation, not this AA minimum |
| Keyboard | 2.1.1 A | Operable controls and no keyboard trap |
| Focus | 2.4.7 AA, 2.4.11 AA | Visible focus; author content doesn't entirely obscure the focused component |
| Reflow | 1.4.10 AA | Test at 320 CSS px equivalent width; exceptions exist for inherently two-dimensional content |
| Errors | 3.3.1 A / 3.3.2 A | Identify the error in text and provide labels/instructions |
| Status | 4.1.3 AA | Programmatically announce status without unnecessarily moving focus |

Focus Appearance (2.4.13) is **AAA**, not a universal AA requirement. WCAG's
inactive-control contrast exception does not make an unexplained disabled CTA
usable. State why it is unavailable and how to proceed. A contrast ratio must
meet the actual threshold before rounding; 4.499 isn't a passing 4.5 result.

Use native `<button>`, `<a href>`, `<input>`, `<label>`, `<fieldset>` and `<legend>`
where they fit. Associate help/errors using `aria-describedby`; mark invalid
fields using `aria-invalid` after validation. Preserve input and focus the first
invalid field or a linked error summary on submit. Never use placeholder text as
the only label. Give repeated item actions distinct accessible names.

Use a polite live status (`role="status"`) for saves/loading completion and a
deliberate alert for actionable errors. Don't announce every streamed token or
re-render an entire list unnecessarily. Keep the focused element stable; after
deleting an item, move focus to a logical remaining action or the list heading.

## Dialogs and navigation

A modal must contain its keyboard interaction, have a name, support the appropriate
dismissal path and restore focus to the trigger or logical successor. Use the
native `<dialog>` where appropriate and test its behavior. ARIA alone does not
implement focus management. Follow the W3C dialog pattern for custom dialogs.
Do not move focus to a toast for routine success. Native Telegram popups and
BackButton behavior require actual-client checks; keep web fallbacks usable.

## Localization and user preferences

Set the page's language and appropriate direction. Use logical CSS properties
and meaningful locale formatting; test RTL with real labels and mixed-direction
IDs/amounts. Isolate identifiers when needed instead of reversing whole strings.
Avoid fixed widths for translated labels, flags as languages and inaccessible
emoji-only status. Respect reduced-motion preferences; don't make animation or
haptics the only way to understand a result. Keep enlargement possible and avoid
disabling browser zoom as a universal layout fix.

## Contrast helper limits

The helper covers opaque six-digit hexadecimal sRGB colors. It does not resolve
CSS variables, alpha composition, gradients, anti-aliasing, imagery, disabled
exceptions or accessible names. Measure actual computed colors and interaction
states, then inspect keyboard, semantics and client behavior separately.
