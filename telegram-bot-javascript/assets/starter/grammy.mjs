import { makeGrammy } from './bots.mjs';
const bot = makeGrammy(process.env.TELEGRAM_BOT_TOKEN);
process.once('SIGINT', () => bot.stop());
process.once('SIGTERM', () => bot.stop());
bot.start().catch(error => {
  console.error('Polling failed:', error?.constructor?.name ?? 'Error');
  process.exitCode = 1;
});
