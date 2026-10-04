import { Bot } from 'grammy';
import { conversations, createConversation } from '@grammyjs/conversations';

/** Private-chat dialog factory. Supply JSON-safe, bounded backend operations.
 * saveFeedback must recheck permission and enforce its idempotency key atomically.
 * In-memory conversation state is lost on restart; see the conversation guide.
 */
export function makeFeedbackBot(token, { options = {}, canSubmit, saveFeedback }) {
  if (typeof canSubmit !== 'function' || typeof saveFeedback !== 'function') {
    throw new TypeError('Supply account-check and idempotent persistence operations');
  }
  const bot = new Bot(token, options);
  bot.use(conversations());

  async function feedback(conversation, entered) {
    const owner = entered.from.id;
    const key = `feedback:${entered.me.id}:${owner}:${entered.update.update_id}`;
    const allowed = await conversation.external(() => canSubmit(owner));
    if (allowed !== true) {
      await entered.reply('Feedback is unavailable for this account.');
      return;
    }
    await entered.reply('Describe your feedback in 1–500 characters. Send /cancel to leave.');
    let draft;
    for (let attempt = 0; attempt < 3; attempt++) {
      const answer = await conversation.waitFor('message:text');
      if (answer.from?.id !== owner) continue;
      if (answer.hasCommand('cancel')) {
        await answer.reply('Canceled. Nothing was saved.');
        return;
      }
      const text = answer.message.text.trim();
      if (!text.startsWith('/') && text.length > 0 && [...text].length <= 500) {
        draft = text;
        break;
      }
      await answer.reply('Use 1–500 characters of text, or /cancel.');
    }
    if (draft === undefined) {
      await entered.reply('No feedback saved. Start again with /feedback.');
      return;
    }
    await entered.reply('Send /confirm to save this feedback, or /cancel.');
    for (let attempt = 0; attempt < 3; attempt++) {
      const answer = await conversation.waitFor('message:text');
      if (answer.from?.id !== owner) continue;
      if (answer.hasCommand('cancel')) {
        await answer.reply('Canceled. Nothing was saved.');
        return;
      }
      if (!answer.hasCommand('confirm')) {
        await answer.reply('Send /confirm to save, or /cancel.');
        continue;
      }
      // The external result is replayed, but a crash before conversation state
      // persistence can repeat this operation. The backend owns deduplication.
      try {
        const receipt = await conversation.external(() => saveFeedback({ key, owner, text: draft }));
        if (!receipt || receipt.saved !== true) throw new Error('Unconfirmed save');
      } catch {
        await answer.reply('Saving was not confirmed. Check your saved feedback before starting again.');
        return;
      }
      await answer.reply('Feedback saved. Thank you.');
      return;
    }
    await entered.reply('No feedback saved. Start again with /feedback.');
  }

  bot.use(createConversation(feedback, { id: 'feedback', maxMillisecondsToWait: 5 * 60 * 1000 }));
  bot.command('feedback', async ctx => {
    if (ctx.chat.type !== 'private' || !ctx.from || ctx.from.is_bot) {
      await ctx.reply('Use /feedback in a private chat with this bot.');
      return;
    }
    await ctx.conversation.enter('feedback');
  });
  bot.command('cancel', ctx => ctx.reply('No feedback dialog is active. Use /feedback to begin.'));
  return bot;
}
