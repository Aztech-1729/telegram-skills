import { makeTelegraf } from './bots.mjs';
const bot = makeTelegraf(process.env.TELEGRAM_BOT_TOKEN);
const stop = signal => {
  try { bot.stop(signal); }
  catch (error) {
    if (error instanceof Error && error.message === 'Bot is not running!') {
      // At this pinned version no receiver/handlers exist yet; stop startup.
      process.exit(0);
    }
    console.error('Polling shutdown failed:', error?.constructor?.name ?? 'Error');
    process.exitCode = 1;
  }
};
process.once('SIGINT', () => stop('SIGINT'));
process.once('SIGTERM', () => stop('SIGTERM'));
bot.launch().catch(error => {
  console.error('Polling failed:', error?.constructor?.name ?? 'Error');
  process.exitCode = 1;
});
