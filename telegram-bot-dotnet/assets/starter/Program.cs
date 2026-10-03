using Telegram.Bot;
using Telegram.Bot.Types.Enums;

var token = Environment.GetEnvironmentVariable("TELEGRAM_BOT_TOKEN")
    ?? throw new InvalidOperationException("TELEGRAM_BOT_TOKEN is required");
using var cancellation = new CancellationTokenSource();
var bot = new TelegramBotClient(token, cancellationToken: cancellation.Token);
bot.OnError += (exception, source) =>
{
    Console.Error.WriteLine($"{source}: {exception.GetType().Name}");
    return Task.CompletedTask;
};
bot.OnMessage += async (message, type) =>
{
    if (type != UpdateType.Message || message.Text is null) return;
    await bot.SendMessage(message.Chat.Id, message.Text, cancellationToken: cancellation.Token);
};
Console.CancelKeyPress += (_, args) => { args.Cancel = true; cancellation.Cancel(); };
Console.WriteLine("Bot started. Press Ctrl+C to stop.");
try { await Task.Delay(Timeout.Infinite, cancellation.Token); }
catch (OperationCanceledException) when (cancellation.IsCancellationRequested) { }
