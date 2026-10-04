# Primary design sources

Reviewed **2026-10-04**. These references establish platform behavior; hierarchy,
wording and flow patterns in this skill are original recommendations.

- [Telegram bot guidelines](https://core.telegram.org/bots/guidelines): /start, interaction methods and navigation. These are product guidelines, not protocol limits.
- [InlineKeyboardButton](https://core.telegram.org/bots/api#inlinekeyboardbutton) and [KeyboardButton](https://core.telegram.org/bots/api#keyboardbutton): Bot API 10.3, action fields and native primary/success/danger styles.
- [RichMessageButton](https://core.telegram.org/bots/api#richmessagebutton): separate rich-button schema, including link styling.
- [Telegram Mini Apps](https://core.telegram.org/bots/webapps#bottombutton): native bottom-button color APIs are separate from bot keyboards.
- [W3C use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html): color alone is insufficient to communicate meaning in web content; the same design principle benefits bot labels.

No live Telegram appearance, conversion measurement or universal client support
claim is made. Check the installed SDK separately from the server API.
