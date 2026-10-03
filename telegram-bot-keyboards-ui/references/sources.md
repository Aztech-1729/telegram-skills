# Sources and compatibility ledger

Checked: **2026-10-03**. Cutoff: **2026-10-03**. Primary references only. These are documentation checks; no Telegram/client smoke test or SDK-wide compatibility certification was performed.

| Primary source | Checked scope / version |
|---|---|
| [Bot API](https://core.telegram.org/bots/api) | Current page lists Bot API **10.3, 2026-08-24** |
| [Bot API changelog](https://core.telegram.org/bots/api-changelog) | 7.11 copy text; 9.4 style/custom-emoji buttons; 9.5 date-time; 10.3 disabled buttons/force reply |
| [InlineKeyboardButton](https://core.telegram.org/bots/api#inlinekeyboardbutton) / [KeyboardButton](https://core.telegram.org/bots/api#keyboardbutton) | Action/appearance distinction, chat constraints, semantic style values |
| [Formatting options](https://core.telegram.org/bots/api#formatting-options) / [MessageEntity](https://core.telegram.org/bots/api#messageentity) | HTML/MarkdownV2, UTF-16 ranges, custom emoji and date-time names |
| [Inline mode](https://core.telegram.org/bots/api#inline-mode) / [setMessageReaction](https://core.telegram.org/bots/api#setmessagereaction) | Result limit/cache/cursors; reaction-specific permissions |
| [PTB InlineKeyboardButton v22.8](https://docs.python-telegram-bot.org/en/v22.8/telegram.inlinekeyboardbutton.html) | Native style/icon support added in **22.7**; client fallback note; 22.8 inspected constructor lacks `disabled` |
| [PTB v22.8 release](https://github.com/python-telegram-bot/python-telegram-bot/releases/tag/v22.8) | Published **2026-06-12** (GitHub release metadata); do not infer all Bot API 10.3 fields are covered |
| [aiogram InlineKeyboardButton v3.31.0](https://docs.aiogram.dev/en/v3.31.0/api/types/inline_keyboard_button.html) / [changelog](https://docs.aiogram.dev/en/v3.31.0/changelog.html) | **3.31.0, 2026-08-26**, Bot API 10.3 release; exact typed model remains the SDK authority |

Local helpers target Python 3.10+ and use only the standard library. Callback schemas, clamping behavior and authorization policy in this skill are original application choices, not Telegram requirements. Keep dependency versions explicit in generated projects; distinguish server API, wrapper library and client rendering support.
