import { makeGrammy } from './bots.mjs';
const bot = makeGrammy(process.env.TELEGRAM_BOT_TOKEN);
const stop = () => bot.stop().catch(error => {
  console.error('Polling shutdown failed:', error?.constructor?.name ?? 'Error');
  process.exitCode = 1;
});
process.once('SIGINT', stop);
process.once('SIGTERM', stop);
bot.start().catch(error => {
  console.error('Polling failed:', error?.constructor?.name ?? 'Error');
  process.exitCode = 1;
});
