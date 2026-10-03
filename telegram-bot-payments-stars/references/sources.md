# Sources and compatibility ledger

Checked: **2026-10-03**. Cutoff: **2026-10-03**. Only primary sources; prices/eligibility must be checked again before live operations.

| Primary source | Checked scope / baseline |
|---|---|
| [Bot API](https://core.telegram.org/bots/api) / [changelog](https://core.telegram.org/bots/api-changelog) | **10.3, 2026-08-24**; 10.2 subscription state updates |
| [Stars guide](https://core.telegram.org/bots/payments-stars) | Digital-goods rail, fulfillment sequence, support/refund responsibilities |
| [Provider payments](https://core.telegram.org/bots/payments) / [currency exponents](https://core.telegram.org/bots/payments/currencies.json) | Physical-goods checkout and currency amounts; no provider-availability guarantee |
| [sendInvoice](https://core.telegram.org/bots/api#sendinvoice) / [createInvoiceLink](https://core.telegram.org/bots/api#createinvoicelink) | Empty Stars provider token, one price, payload size, recurring-link parameters |
| [SuccessfulPayment](https://core.telegram.org/bots/api#successfulpayment) / [BotSubscriptionUpdated](https://core.telegram.org/bots/api#botsubscriptionupdated) | Charge IDs, recurring expiry/flags and renewal-state update |
| [refundStarPayment](https://core.telegram.org/bots/api#refundstarpayment) / [editUserStarSubscription](https://core.telegram.org/bots/api#edituserstarsubscription) | User-bound refund and renewal controls |
| [getMyStarBalance](https://core.telegram.org/bots/api#getmystarbalance) / [getStarTransactions](https://core.telegram.org/bots/api#getstartransactions) | Separate balance/history, 1–100 history page size |
| [giftPremiumSubscription](https://core.telegram.org/bots/api#giftpremiumsubscription) / [getAvailableGifts](https://core.telegram.org/bots/api#getavailablegifts) | Checked duration/Star-price pairs and gift discovery |
| [PTB Bot](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html) | Stable page identified as **v22.8**; Python snake-case wrapper namespace; check individual method signature |
| [aiogram v3.31.0](https://docs.aiogram.dev/en/v3.31.0/api/methods/create_invoice_link.html) / [release](https://github.com/aiogram/aiogram/releases/tag/v3.31.0) | 3.31.0, 2026-08-26; versioned recurring invoice wrapper |

Application recommendations (unique orders, inbox/outbox, atomic credit changes, replay rejection, refund states) are original engineering guidance. Local ledger targets Python 3.10+ and SQLite, supports one-time XTR credits only, and contains no network operations. Recurring methods are documented integration fragments, not a bundled subscription service. No payment, gift, refund, provider onboarding or withdrawal was performed during validation.
