using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;

internal static class EchoSelfTest
{
    internal static void Run()
    {
        var topic = new Message
        {
            Chat = new Chat { Id = -1001234567890, Type = ChatType.Supergroup },
            Text = "<plain & text>", IsTopicMessage = true, MessageThreadId = 42,
        };
        var reply = Echo.BuildReply(topic, UpdateType.Message)
            ?? throw new Exception("Original text message was ignored");
        if (reply.ChatId.Identifier != topic.Chat.Id || reply.MessageThreadId != 42
            || reply.Text != topic.Text || reply.ParseMode != ParseMode.None)
            throw new Exception("Echo routing or plain-text payload changed");
        if (Echo.BuildReply(topic, UpdateType.EditedMessage) is not null
            || Echo.BuildReply(topic, UpdateType.BusinessMessage) is not null
            || Echo.BuildReply(new Message { Chat = topic.Chat }, UpdateType.Message) is not null)
            throw new Exception("Unsupported message variant was echoed");
        topic.IsTopicMessage = false;
        if (Echo.BuildReply(topic, UpdateType.Message)?.MessageThreadId is not null)
            throw new Exception("Non-topic message acquired a thread");
        topic.DirectMessagesTopic = new DirectMessagesTopic { TopicId = 42 };
        if (Echo.BuildReply(topic, UpdateType.Message)?.DirectMessagesTopicId != 42)
            throw new Exception("Direct-message topic was lost");
        Console.WriteLine("Offline echo routing checks passed (no Telegram client created).");
    }
}
