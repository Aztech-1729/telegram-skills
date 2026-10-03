# Payment implementation guide

Checked 2026-10-03. Contents: rails/orders; invoices and handlers; recurring lifecycle; refunds/reconciliation; physical shipping; gifts and Mini Apps. [Sources](sources.md) record the checked API/library baseline. Code fragments do not register live bots or perform payments by themselves.

## Rail and order design

Use [Stars for digital goods/services](https://core.telegram.org/bots/payments-stars) inside Telegram. Provider payments apply to eligible physical products/services; provider/country availability and onboarding require a current check, not a blanket Stripe guarantee. Read [physical-goods payments](https://core.telegram.org/bots/payments).

Store an opaque order payload, intended buyer, product/version, currency, integer amount, entitlement units or subscription identity, status and checkout expiry. Keep IDs independent from mutable usernames. Restrict one-buyer invoices in application validation; shared invoices otherwise may be payable by other users. Do not embed a secret or blindly trust client prices. Treat order state, payment receipt and entitlement change as related but separate records.

The included [ledger](../scripts/payment_ledger.py) supports one-time XTR credit orders. In one SQLite transaction it matches the recorded buyer/currency/amount, stores a unique charge and grants units. Concurrent identical events grant once; conflicting events fail. An unexpected **new** charge for the same one-time order needs reconciliation/refund handling, not another silent grant. Persist the raw trusted update in your inbox before processing so unexpected paid events remain available to operators.

The library cannot guarantee exactly-once external fulfillment. For email, downloads from another service or external credits, commit a fulfillment outbox in the same transaction, then deliver with a stable application idempotency key. Never hold the DB transaction open across Telegram/network I/O.

## Stars invoice and handler fragments

For Stars use XTR, one `LabeledPrice`, integer Stars and `provider_token=""`. With an SDK that documents omission, omission is equivalent; do not reject a legitimate empty token. Payload is 1–128 UTF-8 bytes. Do not request shipping, tips or unnecessary billing data for Stars. Current raw schema: [sendInvoice](https://core.telegram.org/bots/api#sendinvoice).

PTB v22.8 integration fragment (the application supplies a configured bot, ledger, price/order creation and handlers):

```python
import asyncio
import secrets
import time
from telegram import LabeledPrice
from telegram.ext import CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters

async def buy(update, context):
    user_id = update.effective_user.id
    payload = "credits:" + secrets.token_urlsafe(18)
    await asyncio.to_thread(ledger.create_order, payload, user_id, 100, 25,
                            expires=int(time.time()) + 900)
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id, title="25 credits",
        description="One-time credit pack", payload=payload,
        provider_token="", currency="XTR", prices=[LabeledPrice("25 credits", 100)],
    )

async def pre_checkout(update, context):
    q = update.pre_checkout_query
    ok = await asyncio.to_thread(
        ledger.validate_checkout, q.invoice_payload, q.from_user.id,
        q.currency, q.total_amount, now=int(time.time()),
    )
    await q.answer(ok=ok, error_message=None if ok else "Order unavailable. Please create a new invoice.")

async def paid(update, context):
    p = update.effective_message.successful_payment
    applied = await asyncio.to_thread(
        ledger.accept_payment, p.telegram_payment_charge_id, p.invoice_payload,
        update.effective_user.id, p.currency, p.total_amount,
    )
    if applied:
        await update.effective_message.reply_text("Your credits have been added.")

app.add_handler(CommandHandler("buy", buy))
app.add_handler(PreCheckoutQueryHandler(pre_checkout))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid))
```

This fragment assumes `ledger` is an initialized `PaymentLedger` and `app` is the application's PTB Application. Store/retry unexpected paid events through an inbox and alert on mismatch. Set a short bounded DB/query timeout so a failure produces a declined pre-checkout before its ten-second deadline; do not wait on external inventory services indefinitely.

aiogram 3 handler fragment uses the same service:

```python
import asyncio
import time
from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

router = Router()

@router.pre_checkout_query()
async def check(q: PreCheckoutQuery):
    ok = await asyncio.to_thread(
        ledger.validate_checkout, q.invoice_payload, q.from_user.id,
        q.currency, q.total_amount, now=int(time.time()),
    )
    await q.answer(ok=ok, error_message=None if ok else "Order unavailable.")

@router.message(F.successful_payment)
async def receive_payment(message: Message):
    p = message.successful_payment
    if message.from_user is None:
        raise ValueError("payment sender required")
    applied = await asyncio.to_thread(
        ledger.accept_payment, p.telegram_payment_charge_id, p.invoice_payload,
        message.from_user.id, p.currency, p.total_amount,
    )
    if applied:
        await message.answer("Your credits have been added.")
```

Attach this router to the application and use `bot.send_invoice` with the same order/invoice fields as above. Neither example supplies a global error policy, fraud policy, inventory reservation or external fulfillment adapter.

## Real recurring lifecycle

Recurring bot subscriptions are created through [createInvoiceLink](https://core.telegram.org/bots/api#createinvoicelink), not a label on an ordinary invoice. Current documented XTR subscription period is `2592000` seconds (30 days), with a maximum subscription price of 10000 Stars. Create a distinct subscription order/payload for each subscription contract; multiple concurrent contracts can belong to one user.

PTB integration fragment:

```python
from telegram import LabeledPrice

link = await bot.create_invoice_link(
    title="Monthly Pro", description="Renews every 30 days",
    payload=subscription_order_id, provider_token="", currency="XTR",
    prices=[LabeledPrice("Monthly Pro", 250)],
    subscription_period=2592000,
)
# Present link to the intended user or use Telegram.WebApp.openInvoice(link).
```

In aiogram the equivalent method is `bot.create_invoice_link` with `aiogram.types.LabeledPrice`; validate installed SDK support for `subscription_period`. Persist each successful renewal charge independently. Use the server-supplied `subscription_expiration_date` and recurring/first-recurring flags; do not add 30 days repeatedly on duplicate receipt. Take the maximum **trusted confirmed** expiry for that subscription when deliveries are out of order.

Track entitlement expiry separately from renewal state. Bot API 10.2 introduced `Update.subscription`/`BotSubscriptionUpdated` with canceled, active and failed states; these events update renewal state, not paid-through entitlement by themselves. Because the update identifies user/payload, unique per-contract payloads avoid ambiguity. Include the update type in the receiver and check the wrapper's actual support.

Use [editUserStarSubscription](https://core.telegram.org/bots/api#edituserstarsubscription) with user ID, the recorded subscription charge ID and `is_canceled=True` to stop renewal; `False` supports the documented re-enable path. Keep already-paid access until expiry. A failed renewal should not create new paid access. Channel membership subscriptions use their own invite-link methods; distinguish them from bot service subscriptions.

The included one-time ledger intentionally rejects a second charge for an order and therefore **must not** be used as the recurring ledger. Build recurring tables with unique charge IDs, subscription-contract keys and paid-through timestamps; test duplicate, out-of-order, concurrent renewal and cancellation before deploying them.

## Refunds, balance and reconciliation

[refundStarPayment](https://core.telegram.org/bots/api#refundstarpayment) accepts the original user ID and Telegram payment charge ID. Request only within the user's authorized refund scope. Persist a refund request state before calling; mark completion after trusted success/confirmation. On an ambiguous transport failure, reconcile rather than blindly repeating the operation. A refunded-payment update is another reconciliation signal; duplicates must not reverse entitlement twice.

```python
await bot.refund_star_payment(user_id=recorded_user_id,
                             telegram_payment_charge_id=recorded_charge_id)
# Only after confirmed success, record the completed refund in your service.
```

The helper's `record_completed_refund` reverses the original credited units once and does not request refunds. In an application where credits were already consumed this may create debt; define restriction/manual-review policy instead of assuming balances cannot become negative. Recurring refunds require a period/contract-specific entitlement policy, not the one-time helper.

Use `getMyStarBalance` for bot balance and `getStarTransactions(offset, limit)` for history; the return field is `transactions`, not `star_transactions`. Current per-page limit is 1–100. Reconcile incoming and outgoing records, including refunds/chargebacks and paid-broadcast fees; a transaction ID can coincide with the original payment/refund, so include direction/type in a history key. Fragment handles eligible earned-Star reward/withdrawal flows; do not invent a Bot API withdrawal method or guarantee timing/exchange value.

Keep a payment support path, terms/refund policy and `/paysupport` handling as required by the [Stars guide](https://core.telegram.org/bots/payments-stars). Preserve financial audit data while minimizing retained personal data.

## Physical goods and shipping

Use the provider token from BotFather and the provider's supported currency/region. Derive amounts using [currencies.json](https://core.telegram.org/bots/payments/currencies.json), never float multiplication or a universal cents assumption. If flexible shipping is needed, set `need_shipping_address` and `is_flexible`, receive `shipping_query`, and answer with region-appropriate `ShippingOption` values. Shipping option IDs are strings.

Choose one shipping-price model: item-only initial prices plus selected shipping option, or fixed shipping with no flexible options. Do not double-count shipping in both. Revalidate selected shipping and final total on pre-checkout. Payment completion still requires the successful-payment handler; provider disputes/refunds need the provider's process rather than `refundStarPayment`.

Webhook allowed updates must include message, pre-checkout and, where used, shipping/subscription update types. Verify the webhook secret header and deduplicate receipts. Provider and bot tokens belong in secret storage; do not log either.

## Gifts and Mini Apps

Use [getAvailableGifts](https://core.telegram.org/bots/api#getavailablegifts) to discover gift IDs/price metadata; `sendGift` spends bot Stars, and business-account gift management has separate connection/right requirements. User/chat gift-list, unique-gift and upgrade/transfer APIs have distinct purposes; do not guess method/permission equivalence. Consult current gift sections before automating spending.

[giftPremiumSubscription](https://core.telegram.org/bots/api#giftpremiumsubscription) accepts documented duration/price pairs, not a freely chosen per-month rate. The checked 2026-10-03 schema lists 3/6/12 months with 1000/1500/2500 Stars respectively; recheck before a live gift. No helper here spends Stars.

For Mini Apps, create invoices on an authenticated backend, bind orders to the verified session user, then open the returned invoice link. Grant goods from the bot's trusted payment update. Use the Mini Apps skill for HMAC/freshness/session handling instead of duplicating a lossy query-splitting validator.

## Offline validation

```text
python -m unittest discover -s telegram-bot-payments-stars/scripts -p 'test_*.py' -v
```

The standard-library tests cover amount/user/currency mismatches, checkout expiry, concurrent duplicate charge delivery, conflicting replay rollback, database reopening, and user-bound idempotent refund bookkeeping. They make no Telegram requests and prove only the one-time local-ledger behavior.
