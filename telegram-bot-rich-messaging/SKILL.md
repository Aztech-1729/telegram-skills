---
name: |
  telegram-bot-rich-messaging
description: |
  Load this skill for pro-level Telegram bot message/UI design: Rich Messages (Rich Markdown GFM + Rich HTML for reports and AI-streamed answers), full formatting entity reference, custom emoji and date-time entities, emoji-design systems, shop/product-list bot layouts (price tables, auto-order buttons), message templates, and a complete premium storefront bot example with modern styling.
---

# Rich Messaging & Pro Bot UI Design

This skill is the design layer: how to make bot messages look genuinely professional — product lists, reports, menus, AI answers — using every formatting primitive Telegram offers (Bot API 10.x, late 2026).

## 1. Rich Messages (latest Bot API) — structured answers at last

Rich messages are designed for **highly structured responses: reports, AI-streamed answers, documentation snippets, technical papers** and similarly complex content. They support **Rich Markdown** and **Rich HTML** ([Telegram Bot Features](search-result://xYF2fKHJ)).

- **Rich Markdown** follows GitHub Flavored Markdown where possible (headings, tables, lists, code fences, links...) and can include supported HTML tags directly in the same message.
- **Rich HTML** gives document-like structure.
- **API surface (Bot API 10.1–10.3, verified Oct 2026)**: send via the **`sendRichMessage`** method. Structure content as **`InputRichBlock`** building blocks: 10.2 added `InputRichBlockSlideshow`, `InputRichBlockCollage`, tables, headings, quotations, details (collapsible), and media blocks; **10.3 added Rich Message buttons** (inline buttons inside rich messages). `InputRichMessageMedia` + the `media` field let you explicitly specify media used in markdown/html formatting (inline images).
- Rich Messages are outbound-only: inbound user messages still arrive as plain text/markdown — no inbound rich parsing needed.
- Official AI features for bots: https://core.telegram.org/api/bots/ai — includes **`sendMessageDraft` / `sendRichMessageDraft`** for temporary streamed responses while AI generation is in progress (see §6).

Use them when a plain 4096-char HTML message isn't enough: AI bot answers with headings/tables, generated reports, changelogs. Keep a plain-HTML fallback for old clients when the content is critical.

## 2. Formatting entity reference (complete cheat sheet)

HTML mode tags (all current):

```html
<b>/<strong>  <i>/<em>  <u>/<ins>  <s>/<strike>/<del>
<span class="tg-spoiler">, <tg-spoiler>
<blockquote>, <blockquote expandable>
<pre>, <pre><code class="language-python">
<code>
<a href="...">, <a href="tg://user?id=123">
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
<tg-time unix="1760000000"></tg-time>   <!-- date-time entity, per-user locale -->
```

Only named HTML entities supported: `&lt; &gt; &amp; &quot;` ([Bot API](search-result://HJXafTEt)).

MarkdownV2: `*bold* _italic_ __underline__ ~strikethrough~ ||spoiler|| [text](url) [name](tg://user?id=1) ![👍](tg://emoji?id=5368324170671202286) ![time](tg://time?unix=1647531900&format=r)` + backticks for code ([grammY ParseMode reference](search-result://kdz161b9)). Escape: `_ * [ ] ( ) ~ \` > # + - = | { } . !`.

Entity-based sending (no parse mode — never breaks on invalid markup):

```python
# PTB
MessageEntity(MessageEntity.BOLD, offset=0, length=4), ...
await bot.send_message(chat_id, plain_text, entities=entities)
# aiogram
MessageEntity(type="bold", offset=0, length=4)
```

Offsets/lengths are in **UTF-16 code units** (emoji count as 2), not Python characters — compute with a helper when mixing emoji and formatting ([entities doc](search-result://2rl9Y6JJ)).

## 3. Design system for bot text (pro emoji + layout patterns)

Rules used by the best-looking bots (shop, finance, AI):

1. **One emoji per line-role, consistently**: 📌 headers, 💰 price, ✅/⭐ status, 🔥 hot, 🆕 new, 📦 products, ⚠️ warnings, ❌ errors, ℹ️ info.
2. **Headers**: bold + emoji, blank line after. `📌 <b>MY SHOP</b>\n\n`
3. **Lists**: `•` or emoji markers with fixed column feel: `🎧 ElevenLabs — <b>$4</b>`
4. **Monospace for data**: prices, codes, IDs in `<code>$4</code>` so they align visually.
5. **Quotes for terms**: `<blockquote expandable>` for long rules/FAQs.
6. **Spoilers** for answers in quiz bots; **tg-time** for expiries; reactions for quick feedback.
7. Never exceed ~25 lines per message — paginate instead.

### Product/price list layout (the storefront pattern)

```python
PRODUCTS = [
    ("🎧", "ElevenLabs", 4, "1 Month"),
    ("🎵", "Minimax", 3, "1 Month"),
    ("✨", "Gemini 18m", 5, "Full Access"),
    ("💼", "ChatGPT Business", 12, "1 Month"),
    ("🚀", "ChatGPT Plus", 9, "1 Month"),
    ("🤖", "Claude Pro", 10, "1 Month"),
    ("🧠", "Cursor Pro", 8, "1 Month"),
    ("🎬", "YTB Premium", 2, "1 Month"),
    ("🎨", "Adobe CC", 6, "1 Year"),
]

def catalog_text(page=0, per_page=6) -> str:
    rows = PRODUCTS[page*per_page:(page+1)*per_page]
    lines = [
        "🌟 <b>AZ TECH SHOP</b> 🌟",
        "<i>Verified • Instant • Auto-delivery</i>",
        "",
    ]
    for emoji, name, price, note in rows:
        lines.append(f"{emoji} <b>{name}</b> — <code>${price}</code> {note}")
    lines += ["", f"⭐ <b>{sum(p[2] for p in rows):,}</b> orders delivered ✅"]
    return "\n".join(lines)
```

Pair with an inline keyboard of buy buttons, one row per product or a grid:

```python
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def catalog_kb(page=0, per_page=6) -> InlineKeyboardMarkup:
    rows = PRODUCTS[page*per_page:(page+1)*per_page]
    kb = []
    # 2 products per row of buttons — compact grid
    for i in range(0, len(rows), 2):
        row = [InlineKeyboardButton(f"{e} {n} ${p}", callback_data=f"buy:{page}:{j}")
               for j, (e, n, p, _) in enumerate(rows[i:i+2], start=i)]
        kb.append(row)
    # navigation + support
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cat:{page-1}"))
    if (page+1)*per_page < len(PRODUCTS):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"cat:{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("🛒 Cart", callback_data="cart"),
               InlineKeyboardButton("🎧 Support", url="https://t.me/yourshop")])
    kb.append([InlineKeyboardButton("💳 Pay with Stars", callback_data="pay:stars")])
    return InlineKeyboardMarkup(kb)

# pagination handler edits the SAME message (never re-sends):
async def catalog(update, context):
    await update.message.reply_text(catalog_text(), reply_markup=catalog_kb())

async def on_cat(update, context):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split(":")[1])
    await q.edit_message_text(catalog_text(page), reply_markup=catalog_kb(page))
```

`aiogram` equivalents: `InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=..., callback_data=...)]])` and `cb.message.edit_text(...)` — identical layout logic.

## 4. Complete premium storefront bot (full example)

Combines: catalog + per-product order flow + Stars payment + receipt + admin panel.

```python
# main.py — python-telegram-bot v22
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, PreCheckoutQueryHandler, ContextTypes,
                          filters)

logging.basicConfig(level=logging.INFO)

PRODUCTS = {  # key → (emoji, name, price_stars, note)
    "el": ("🎧", "ElevenLabs", 40, "1 Month"),
    "gpt": ("🚀", "ChatGPT Plus", 90, "1 Month"),
    "cc": ("🎨", "Adobe CC", 60, "1 Year"),
    "gem": ("✨", "Gemini 18m", 50, "Full Access"),
}
ADMINS = {123456789}  # config: your user id

def home_kb() -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(f"{e} {n} ⭐{p}", callback_data=f"buy:{k}")]
          for k, (e, n, p, _) in PRODUCTS.items()]
    kb.append([InlineKeyboardButton("🎧 Support", url="https://t.me/yourshop"),
               InlineKeyboardButton("ℹ️ About", callback_data="about")])
    return InlineKeyboardMarkup(kb)

HOME_TEXT = ("🌟 <b>AZ TECH SHOP</b> 🌟\n"
             "<i>Instant auto-delivery • 24/7</i>\n\n"
             "Select a product to order 👇")

async def start(update: Update, context):
    # deep link support: /start buy_gpt
    if context.args and context.args[0].startswith("buy_"):
        return await open_product(update, context, context.args[0][4:])
    await update.message.reply_text(HOME_TEXT, reply_markup=home_kb())

async def open_product(update: Update, context, key):
    e, n, p, note = PRODUCTS[key]
    text = (f"{e} <b>{n}</b>\n\n"
            f"💰 Price: <code>{p} Stars</code>\n"
            f"📦 {note}\n"
            f"⚡ Delivery: instant after payment\n\n"
            f"Proceed to checkout?")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Pay {p} ⭐", callback_data=f"pay:{key}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")],
    ])
    if update.message:
        await update.message.reply_text(text, reply_markup=kb)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=kb)

async def on_button(update: Update, context):
    q = update.callback_query
    await q.answer()
    action = q.data.split(":")[0]
    if action == "home":
        await q.edit_message_text(HOME_TEXT, reply_markup=home_kb())
    elif action == "buy":
        await open_product(update, context, q.data.split(":")[1])
    elif action == "pay":
        key = q.data.split(":")[1]
        _, name, stars, _ = PRODUCTS[key]
        await context.bot.send_invoice(
            chat_id=q.message.chat.id, title=name,
            description=f"{name} — auto delivery",
            payload=f"order:{key}:{q.from_user.id}",
            currency="XTR", prices=[LabeledPrice(name, stars)],
        )
    elif action == "about":
        await q.edit_message_text(
            "ℹ️ <b>About us</b>\nTrusted seller since 2024.\n"
            "<blockquote expandable>Full terms: delivery is instant, refund within 24h if the key is unused. "
            "Contact support for any issue.</blockquote>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]]))

async def pre_checkout(update: Update, context):
    payload = update.pre_checkout_query.invoice_payload  # validate order exists!
    await update.pre_checkout_query.answer(ok=True)

# Your business logic — replace with real implementations:
def deliver_product(key: str, uid: int):
    """Fulfill the order: send the key/license to the buyer (or log for manual)."""
    ...

def generate_license(context, uid: int, key: str) -> str:
    """Return the product key. Load from a keys DB, mark it sold (idempotently)."""
    ...

async def paid(update: Update, context):
    p = update.message.successful_payment
    _, key, uid = p.invoice_payload.split(":")
    deliver_product(key, uid)  # idempotent by p.telegram_payment_charge_id
    await update.message.reply_text(
        "✅ <b>Payment received!</b>\n\n"
        "📦 Delivery: <tg-time unix=\"1760000100\" format=\"r\"></tg-time>\n\n"
        "Tap below to get your product 👇",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Get product", callback_data=f"dl:{key}")]]))

async def dl(update: Update, context):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(f"🔑 <code>{generate_license(context, q.from_user.id, q.data[3:])}</code>")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # NOTE: pattern-specific handlers MUST be registered before the generic
    # on_button handler — PTB matches first-registered-wins within a group.
    app.add_handler(CallbackQueryHandler(dl, pattern="^dl:"))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid))
    app.run_polling()
```

Design details that make it look "premium":
- Emoji as product icons (🎧 🎨 🚀) — instant visual identity without images.
- `<code>` for prices/keys (monospace = "data" feel, aligns).
- `<tg-time format="r">` → every user sees the delivery ETA in their own language/timezone.
- `<blockquote expandable>` for terms — collapsible, no wall of text.
- ✅/❌ semantics on buttons; ⬅️ consistent "Back" on every screen; one message edited through the whole flow.
- Deep links `t.me/YourShopBot?start=buy_gpt` per product → per-product promo posts.

## 5. Report / dashboard message pattern

```python
def report(stats: dict) -> str:
    return f"""📊 <b>Weekly Report</b> — <tg-time unix="1760000000" format="wDT"></tg-time>

<b>Revenue</b>
• Orders: <code>{stats['orders']}</code> (+{stats['orders_delta']}% 🔥)
• Stars in: <code>{stats['stars']}</code>

<b>Top products</b>
1. 🚀 ChatGPT Plus — <code>{stats['top1']}</code>
2. 🎨 Adobe CC — <code>{stats['top2']}</code>

<blockquote expandable><b>Details</b>
Full breakdown per day, refunds and churn here...</blockquote>
"""
```

For genuinely tabular output, Rich Markdown tables (GFM) in a Rich message render as real tables — the cleanest option for dense numbers ([Bot Features](search-result://xYF2fKHJ)).

## 6. AI-answer streaming pattern (Bot API 10.x — two options)

### Option A — native streaming drafts (preferred, newest API)

Bot API 10.x provides **`sendMessageDraft` / `sendRichMessageDraft`**: temporary streamed responses shown while generation is in progress — no manual edit loop, no 429 risk from editing.

```python
# During generation: repeatedly send/update a draft
await bot.send_message_draft(chat_id, partial_text)        # plain draft
await bot.send_rich_message_draft(chat_id, rich_blocks)   # rich draft
# When generation completes, send the final message (draft disappears)
await bot.send_message(chat_id, final_text)
# Throttle/coalesce draft updates to respect Telegram's draft rate limits;
# propagate user "stop" to cancel the underlying generation job.
```

Drafts are for **users/private chats** — do not use streaming drafts in broadcast channels.

### Option B — manual edit loop (works on any API version)

```python
# 1) send a placeholder instantly
msg = await update.message.reply_text("✍️ <i>Thinking…</i>")
# 2) edit as chunks arrive — throttle to ~1 edit/second (429 otherwise)
buf = ""
async for chunk in ai_stream():
    buf += chunk
    if time.time() - last_edit >= 1.0:
        await msg.edit_text(buf[:4000] + " ▌")
        last_edit = time.time()
# 3) final render: Rich Message for structured answers
await msg.edit_text(render_rich_or_html(buf))
```

## 7. UX checklist for "pro max" bot UI

- [ ] Consistent emoji vocabulary across all messages (one system, everywhere)
- [ ] Prices/codes/IDs always in `<code>`
- [ ] All flows edit ONE message (no message spam per tap)
- [ ] Every screen has Back + Support affordances
- [ ] `<tg-time>` instead of hardcoded date strings
- [ ] Expandable quotes for T&C/FAQ; spoilers for answers/keys
- [ ] Rich Markdown for tables/reports; plain HTML fallback
- [ ] Deep links per product/section for promo posts
- [ ] Reactions used for quick feedback (👍 useful prompts)
- [ ] 4096-char limits respected; pagination everywhere
- [ ] Commands registered + `/start` always re-opens home with state cleared
