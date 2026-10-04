using Telegram.Bot;
using Telegram.Bot.Types.Enums;

if (args.SequenceEqual(new[] { "--self-test" }))
{
    EchoSelfTest.Run();
    return;
}
var token = Environment.GetEnvironmentVariable("TELEGRAM_BOT_TOKEN");
if (string.IsNullOrWhiteSpace(token))
    throw new InvalidOperationException("TELEGRAM_BOT_TOKEN is required");
using var cancellation = new CancellationTokenSource();
var bot = new TelegramBotClient(token, cancellationToken: cancellation.Token);
bot.OnError += (exception, source) =>
{
    Console.Error.WriteLine($"{source}: {exception.GetType().Name}");
    return Task.CompletedTask;
};
bot.OnMessage += async (message, type) =>
{
    var request = Echo.BuildReply(message, type);
    if (request is not null) await bot.SendRequest(request, cancellation.Token);
};
Console.CancelKeyPress += (_, args) => { args.Cancel = true; cancellation.Cancel(); };
Console.WriteLine("Bot started. Press Ctrl+C to stop.");
try { await Task.Delay(Timeout.Infinite, cancellation.Token); }
catch (OperationCanceledException) when (cancellation.IsCancellationRequested) { }
