---
name: |
  telegram-bot-payments-stars
description: |
  Load this skill for Telegram bot monetization: Telegram Stars payments (digital goods/services, invoices, pre-checkout flow, refunds, subscriptions), classic payment providers (Stripe etc.) with shipping, gifting Premium via Stars, revenue withdrawal, Star balance checks, gift management methods, and Mini App integration points, with complete code for python-telegram-bot and aiogram.
---

# Telegram Bot Payments: Stars, Invoices & Monetization

## 1. Choosing the payment rail

- **Telegram Stars (XTR)** — the native, required currency for digital goods and services sold in-bot (Bot API enforces Stars for digital products). No provider integration needed; users pay from their Star balance (bought via in-app purchases). Bot revenue is withdrawable via Fragment.
- **Classic providers** (Stripe, and other region-specific providers) — for physical goods and cases where you need real card processing: `send_invoice` with a provider token, optional shipping queries, `successful_payment` message on completion.
- **Gifts** — bots can send gifts, gift Premium subscriptions paid in Stars, read user/chat gift lists, and manage unique-gift info (Bot API 9.0+).
- **Mini App payments** — Stars payments inside Mini Apps plus `WebApp initData` for identity.

Rule: digital goods (subscriptions, features, content unlocks, AI tokens) → **Stars**. Physical goods with shipping → **classic provider**.

## 2. Stars invoice — full flow (PTB)

```python
from telegram import LabeledPrice, Update
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters

async def buy(update, context):
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="100 AI tokens",
        description="Adds 100 AI tokens to your balance",
        payload="tokens-100:{update.effective_user.id}",     # your internal order ID
        currency="XTR",                                       # Stars
        prices=[LabeledPrice(label="100 tokens", amount=100)], # amount in Stars (integer)
    )

async def pre_checkout(update, context):
    query = update.pre_checkout_query
    ok, error = validate_order(query.invoice_payload)   # check payload/stock server-side
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Out of stock, sorry.")

async def successful(update, context):
    p = update.message.successful_payment
    order = p.invoice_payload
    deliver_goods(order)               # ALWAYS deliver here — idempotently!
    await update.message.reply_text(
        f"Payment received: {p.total_amount} {p.currency}. Thanks!"
    )

app.add_handler(CommandHandler("buy", buy))
app.add_handler(PreCheckoutQueryHandler(pre_checkout))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful))
```

Flow: `send_invoice` → user taps Pay → bot receives `pre_checkout_query` → MUST answer within 10s → user completes → bot receives a message with `successful_payment` → deliver.

Rules:
- `answer_pre_checkout_query` is mandatory; if not answered in 10 seconds the payment fails.
- `successful_payment` can be duplicated by Telegram retries — make delivery **idempotent** keyed on `telegram_payment_charge_id`.
- Keep `payload` ≤ 128 bytes; store order state in a DB.

Also possible: `create_invoice_link(...)` returns an HTTPS link you can share anywhere (posts, QR) — it opens the invoice in Telegram.

## 3. Stars invoice — aiogram 3

```python
from aiogram.types import LabeledPrice

@router.message(Command("buy"))
async def buy(message: Message, bot: Bot):
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Pro subscription",
        description="1 month of Pro features",
        payload="pro-1m",
        currency="XTR",
        prices=[LabeledPrice(label="Pro", amount=250)],
    )

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@router.message(F.successful_payment)
async def paid(message: Message):
    p = message.successful_payment
    await message.answer(f"Paid {p.total_amount} ⭐")
```

## 4. Refunds and Star balance

```python
# Refund a Stars payment (PTB)
await context.bot.refund_star_payment(
    user_id, telegram_payment_charge_id,
)
# Balance: get_star_transactions lists all in/out Star transactions (up to 10k entries paginated)
txs = await context.bot.get_star_transactions()
for tx in txs.star_transactions: ...
```

Withdrawal of earned Stars is done via Fragment from BotFather (`/mybots` → Payments → withdraw); not an API call.

## 5. Classic provider payments (physical goods)

```python
async def buy_shirt(update, context):
    await context.bot.send_invoice(
        chat_id, title="T-Shirt", description="100% cotton tee",
        payload="shirt-m",
        provider_token=PROVIDER_TOKEN,     # from @BotFather → /mybots → Payments
        currency="USD",
        prices=[LabeledPrice("T-Shirt", 2999), LabeledPrice("Shipping", 499)],
        need_name=True, need_phone_number=True, need_shipping_address=True,
        is_flexible=True,                  # allows shipping query
    )

# If is_flexible=True, answer the shipping query with options
async def shipping(update, context):
    await context.bot.answer_shipping_query(
        update.shipping_query.id, ok=True,
        shipping_options=[
            ShippingOption(1, "Standard", [LabeledPrice("Standard", 499)]),
            ShippingOption(2, "Express", [LabeledPrice("Express", 1999)]),
        ],
    )
```

Providers are country-dependent; Stripe is broadly available. Provider tokens are managed in BotFather. `successful_payment` handling is identical to Stars.

## 6. Gifts and Premium gifting (Bot API 9.0+)

```python
# Send a gift to a user (Stars are deducted from the bot's balance)
await context.bot.send_gift(user_id, gift_id="gift_id_here", text="Happy birthday!")

# Gift Premium subscription paid in Stars
await context.bot.gift_premium_subscription(
    user_id, month_count=3,
    star_count=750,   # current rate is per month; check docs
    text="Enjoy Premium!",
)

# List gifts owned by a user/chat
await context.bot.get_user_gifts(user_id)
await context.bot.get_chat_gifts(chat_id)

# Business accounts: manage gifts shown on a business account's profile
await context.bot.get_business_account_gifts(connection_id, ...)
# UniqueGift details include model/backdrop/symbol and unique_gift_colors on ChatFullInfo
```

## 7. Mini App integration points

- Open a Mini App from a keyboard button (`web_app=WebAppInfo(url="https://app.example.com")`) or `MenuButton`.
- Inside the Mini App, JS SDK: `Telegram.WebApp.initData` (signed user identity), `Telegram.WebApp.MainButton`, `openInvoice` (Stars payment inside the app), `haptic feedback`, `CloudStorage`, theme params.
- Server side, validate `initData` with HMAC:

```python
import hmac, hashlib

def validate_init_data(init_data: str, bot_token: str) -> bool:
    parsed = dict(pair.split("=", 1) for pair in init_data.split("&"))
    received_hash = parsed.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, received_hash)
```

`parsed["user"]` (after URL-decoding) gives the trusted user ID. Mini App origins are enforced to the registered domain (hardened, enabled for all apps since July 20, 2026 — configure via BotFather).

## 8. Security checklist for payments

- [ ] Validate `pre_checkout_query` payload against your DB (exists, not yet fulfilled, correct price).
- [ ] Delivery is idempotent keyed by `telegram_payment_charge_id`.
- [ ] Never trust the client for price — amounts are defined by your invoice server-side.
- [ ] Refunds logged; Star refunds are API-reversible.
- [ ] `initData` HMAC validated and `auth_date` freshness-checked (e.g. < 24h).
- [ ] Provider tokens and bot token in env vars only.
- [ ] Webhook consumers verify `X-Telegram-Bot-Api-Secret-Token`.

## 9. Common pitfalls

- Sending Stars invoice with a provider token (XTR invoices must have NO provider_token).
- Forgetting `PreCheckoutQueryHandler` → all payments fail with timeout.
- Currency amounts are **minor units** for classic providers (cents), but Stars (`XTR`) amounts are integer Stars.
- Treating `successful_payment` as exactly-once — it is at-least-once; make handlers idempotent.
- Attempting refunds by charge ID of a different user (must match user_id).
- Digital goods via classic provider — Telegram requires Stars for digital goods.
