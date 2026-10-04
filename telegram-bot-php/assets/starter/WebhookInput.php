<?php
declare(strict_types=1);

namespace TelegramStarter;

final class IngressError extends \RuntimeException
{
    public function __construct(public int $status) { parent::__construct('Invalid webhook input'); }
}

function decodeWebhook(string $method, string $secret, string $supplied, string $raw): array
{
    if ($method !== 'POST') { throw new IngressError(405); }
    if ($secret === '') { throw new IngressError(503); }
    if (!hash_equals($secret, $supplied)) { throw new IngressError(403); }
    if (strlen($raw) > 524288) { throw new IngressError(413); }
    try { $payload = json_decode($raw, true, 64, JSON_THROW_ON_ERROR); }
    catch (\JsonException $error) { throw new IngressError(400); }
    if (!is_array($payload) || !isset($payload['update_id'])
        || !is_int($payload['update_id']) || $payload['update_id'] < 0) {
        throw new IngressError(400);
    }
    return $payload;
}

function echoRequest(array $payload): ?array
{
    $message = $payload['message'] ?? null;
    if (!is_array($message) || !isset($message['text'])) { return null; }
    if (!is_array($message['chat'] ?? null) || !is_int($message['chat']['id'] ?? null)
        || !is_string($message['text']) || $message['text'] === '') {
        throw new IngressError(400);
    }
    $request = ['chat_id' => $message['chat']['id'], 'text' => $message['text']];
    if (($message['is_topic_message'] ?? false) === true) {
        $thread = $message['message_thread_id'] ?? null;
        if (!is_int($thread) || $thread <= 0) { throw new IngressError(400); }
        $request['message_thread_id'] = $thread;
    }
    if (isset($message['direct_messages_topic'])) {
        $directTopic = $message['direct_messages_topic'];
        $topicId = is_array($directTopic) ? ($directTopic['topic_id'] ?? null) : null;
        if (!is_int($topicId) || $topicId <= 0) { throw new IngressError(400); }
        $request['direct_messages_topic_id'] = $topicId;
    }
    return $request;
}
