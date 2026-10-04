using Telegram.Bot.Requests;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;

internal static class Echo
{
    internal static SendMessageRequest? BuildReply(Message message, UpdateType type)
    {
        if (type != UpdateType.Message || string.IsNullOrEmpty(message.Text)) return null;
        return new SendMessageRequest
        {
            ChatId = message.Chat.Id,
            Text = message.Text,
            MessageThreadId = message.IsTopicMessage ? message.MessageThreadId : null,
            DirectMessagesTopicId = message.DirectMessagesTopic?.TopicId,
        };
    }
}
