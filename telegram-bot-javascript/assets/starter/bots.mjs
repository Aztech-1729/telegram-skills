import { Bot, InlineKeyboard } from 'grammy';
import { Telegraf, Markup } from 'telegraf';
import { message } from 'telegraf/filters';

export function makeGrammy(token, options = {}) {
  if (!token) throw new Error('TELEGRAM_BOT_TOKEN is required');
  const bot = new Bot(token, options);
  bot.command('start', ctx => ctx.reply('Choose Help or send a message.', {
    reply_markup: new InlineKeyboard().text('Help', 'help')
  }));
  bot.command('help', ctx => ctx.reply('This starter echoes text.'));
  bot.callbackQuery('help', async ctx => {
    await ctx.answerCallbackQuery();
    await ctx.reply('Use /help or send text.');
  });
  bot.on('message:text', ctx => ctx.reply(ctx.message.text));
  bot.catch(err => console.error('Handler failed:', err.error?.constructor?.name ?? 'Error'));
  return bot;
}

export function makeTelegraf(token, options = {}) {
  if (!token) throw new Error('TELEGRAM_BOT_TOKEN is required');
  const bot = new Telegraf(token, options);
  bot.start(ctx => ctx.reply('Choose Help or send a message.', Markup.inlineKeyboard([
    Markup.button.callback('Help', 'help')
  ])));
  bot.help(ctx => ctx.reply('This starter echoes text.'));
  bot.action('help', async ctx => {
    await ctx.answerCbQuery();
    await ctx.reply('Use /help or send text.');
  });
  bot.on(message('text'), ctx => ctx.reply(ctx.message.text));
  bot.catch(err => console.error('Handler failed:', err?.constructor?.name ?? 'Error'));
  return bot;
}
