# Theme, hierarchy and responsive components

Reviewed 2026-10-04. Concrete sizes and fallback colors below are an original
starting system; adapt them to the user's brand, content and measured contrast.

## Color system

| Role | Telegram starting token | Use / caution |
|---|---|---|
| Page | `--tg-theme-bg-color` | Overall surface |
| Secondary surface | `--tg-theme-secondary-bg-color` | Sections and cards; verify separation |
| Text | `--tg-theme-text-color` | Main content, labels and essential instructions |
| Hint | `--tg-theme-hint-color` | Supplemental information only after measuring contrast |
| Links | `--tg-theme-link-color` | Real links; keep underline or another non-color cue |
| Main action pair | `--tg-theme-button-color` + `--tg-theme-button-text-color` | CTA background/text; test the pair, not each color alone |
| Destructive text | `--tg-theme-destructive-text-color` | Consequence text; not automatically a suitable filled-button background |

Fallback example pairs: white on `#1D4ED8` for primary, white on `#166534` for
success, white on `#B91C1C` for danger. They pass normal-text contrast as opaque
sRGB pairs; they are not universal Telegram brand colors. Measure your actual
theme/composited pair, including hover/focus states. Neutral controls use the
surface/text pair rather than pale low-contrast gray. Do not give every card a
saturated background. Never use color alone for invalid, selected or paid states.

The [theme CSS asset](../assets/theme.css) preserves host colors when present.
For a host theme with an insufficient button pair, choose an accessible pair for
your own component or adapt its presentation; don't silently rewrite every
Telegram host color. [The contrast helper](../../telegram-bot-accessibility/scripts/contrast.py)
measures opaque six-digit RGB pairs. Transparency, imagery and gradients need
their actual rendered colors and further inspection.

## Layout and type

Start with a 16px body and about 1.5 line height, a constrained reading width,
fluid fields and an 8px spacing rhythm. These are recommendations, not WCAG
requirements. Prefer content that reflows at 320 CSS px; test enlarged text and
landscape. Let long translated labels wrap instead of truncating the action.
Use a 44px control-height starting point for touch comfort; the WCAG AA 24px
target rule and exceptions are documented in the Accessibility skill.

Use all four `--tg-content-safe-area-inset-*` variables. Avoid adding the same
system inset twice: content safe areas address Telegram overlap, system safe
areas address device UI. Inspect the actual launch mode. Keep the primary action
and focused field reachable above keyboards/native bars. For a fixed footer,
reserve its height in scroll content and test overlap; stable viewport height is
a layout input, not a promise the soft keyboard cannot cover a field.

## Components and states

| Component | Implementation decision |
|---|---|
| Primary button | Verb + object; consistent placement; block duplicate commits while pending |
| Secondary button | Quiet surface/text style; Back/Cancel normally use this role |
| Danger button | Explicit destructive label; confirmation or undo according to consequence |
| Input | Real label, help/error association, appropriate inputmode/autocomplete and backend validation |
| List/card | Named action per item; stable IDs; useful empty/filter state; no entire-card nested button |
| Status | Text, not only spinner/color; polite live status for ordinary progress; alert for actionable errors |
| Dialog | Native popup where suitable; otherwise a tested accessible dialog, focus restoration and dismissal |
| Navigation | Real buttons/links with a clear current location; native BackButton follows app routes |

Don't disable the only way to leave a failed operation. During a write, preserve
typed values and explain uncertain outcomes. Do not render server/browser values
using unsanitized HTML. Loading should settle into a genuine result or an explicit
failure/recovery state; never fill a screen with invented activity metrics.

## Native MainButton, SecondaryButton and BackButton

Telegram's MainButton defaults to the theme's button pair; SecondaryButton has
its own default pair. Use MainButton for the current screen's important action.
Do not also show an identical sticky web CTA unless the design requires a fallback.
SecondaryButton is conditional on API 7.10; BackButton on 6.1. If unsupported,
keep a usable HTML control. `expand()` and fullscreen are separate decisions.

Original integration fragment for a supported client:

```javascript
function attachSave(tg, save, reportError) {
  let busy = false;
  let active = true;
  const onSave = async () => {
    if (busy || !active) return;
    busy = true;
    tg.MainButton.showProgress(); // disabled by default while progress is visible
    try { await save(); }        // caller reports the real result/recovery state
    catch (error) { if (active) reportError(error); }
    finally { busy = false; if (active) tg.MainButton.hideProgress(); }
  };
  tg.MainButton.hideProgress(); // Reset progress left by the previous screen.
  tg.MainButton.setParams({ text: "Save changes", is_active: true, is_visible: true });
  tg.MainButton.onClick(onSave);
  return () => {
    active = false;
    tg.MainButton.offClick(onSave);
    tg.MainButton.hideProgress(); // The obsolete request's finally must not touch a new screen.
    tg.MainButton.hide();
  };
}
```

The caller catches/reports save errors and cancels or ignores obsolete requests
when the screen leaves. Keep a reference to handlers for `offClick`/`offEvent`.
Don't restore an old screen's button state after a newer screen is mounted.
Listen to `themeChanged` for custom computed styles; the SDK updates theme CSS
variables. Subscribe to relevant viewport/safe-area events only where needed.
Haptics are optional feedback, not a substitute for status text or user consent.

## Acceptance

Check light/dark/custom themes, long labels, empty/loading/error states, 320px
reflow, zoom, keyboard focus, soft keyboard, orientation, system/content insets,
Back, canceled prompts, unsupported native APIs and duplicate taps. Document the
actual clients checked; automated unit tests don't certify every Telegram WebView.
