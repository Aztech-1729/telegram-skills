# Observable acceptance scenarios

Record device, client/browser version, theme, locale, assistive technology and
observed result. Use these applicable scenarios, not a blanket certification.

| Scenario | Observe |
|---|---|
| Read a native menu without its colors/icons | Labels and message context still explain actions |
| Long translated labels and RTL text | Wrapping and reading order preserve meaning; amount/ID stays intelligible |
| Light, dark and custom themes | Actual text/control pairs have sufficient contrast |
| Keyboard-only Mini App task | All operations work, focus is visible, no accidental trap |
| Enlarged text / 320 CSS px | Essential content and actions remain reachable without unwanted horizontal scrolling |
| Soft keyboard / native bar / orientation change | Focused field and primary action remain reachable |
| Empty list, validation error, failed save | State is explained; good input remains; next action is available |
| Screen-reader save / delete | Outcome is announced appropriately; focus isn't lost with the removed node |
| Dialog open / dismiss / confirm | Name, focus containment, dismissal and focus return work |
| Reduced motion and absent haptics | All information remains available and the task is usable |
| Stale menu / session expiry | Clear recovery, no misleading success, no unauthorized operation |

Automated checks can find some contrast, markup and behavior failures. Manual
keyboard, screen-reader, viewport and Telegram-client checks remain necessary.
Report any untested scenario as untested. Connect each fix to the observed defect
instead of claiming an arbitrary quality multiplier.
