import { makeTelegraf } from './bots.mjs';
const bot = makeTelegraf(process.env.TELEGRAM_BOT_TOKEN);
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
bot.launch().catch(error => {
  console.error('Polling failed:', error?.constructor?.name ?? 'Error');
  process.exitCode = 1;
});
