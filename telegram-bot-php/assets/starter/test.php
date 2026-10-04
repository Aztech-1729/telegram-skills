<?php
declare(strict_types=1);
require __DIR__ . '/WebhookInput.php';
use TelegramStarter\IngressError;
use function TelegramStarter\decodeWebhook;
use function TelegramStarter\echoRequest;

function check(bool $condition, string $name): void
{
    if (!$condition) { throw new RuntimeException($name); }
}
function rejected(int $status, callable $action): void
{
    try { $action(); } catch (IngressError $error) {
        check($error->status === $status, 'Incorrect rejection status'); return;
    }
    throw new RuntimeException('Invalid webhook accepted');
}
$raw = json_encode(['update_id' => 1, 'message' => ['chat' => ['id' => -1001234567890],
    'text' => '<plain & text>', 'is_topic_message' => true, 'message_thread_id' => 42]], JSON_THROW_ON_ERROR);
$payload = decodeWebhook('POST', 'fixture-secret', 'fixture-secret', $raw);
check(echoRequest($payload) === ['chat_id' => -1001234567890, 'text' => '<plain & text>',
    'message_thread_id' => 42], 'Topic/plain-text routing');
check(echoRequest(['update_id' => 2, 'callback_query' => ['data' => 'help']]) === null, 'Non-message routing');
check(echoRequest(['update_id' => 3, 'edited_message' => $payload['message']]) === null, 'Edit routing');
check(echoRequest(['message' => ['chat' => ['id' => 99], 'text' => 'x',
    'direct_messages_topic' => ['topic_id' => 42]]]) === ['chat_id' => 99, 'text' => 'x',
    'direct_messages_topic_id' => 42], 'Direct-message topic routing');
rejected(405, fn() => decodeWebhook('GET', 's', 's', $raw));
rejected(503, fn() => decodeWebhook('POST', '', '', $raw));
rejected(403, fn() => decodeWebhook('POST', 's', '', $raw));
rejected(403, fn() => decodeWebhook('POST', 's', 'wrong', '{broken-json'));
rejected(413, fn() => decodeWebhook('POST', 's', 's', str_repeat('x', 524289)));
foreach (['{broken', 'null', '[]', '{"update_id":"1"}', '{"update_id":-1}'] as $bad) {
    rejected(400, fn() => decodeWebhook('POST', 's', 's', $bad));
}
rejected(400, fn() => echoRequest(['message' => ['chat' => ['id' => '99'], 'text' => 'x']]));
rejected(400, fn() => echoRequest(['message' => ['chat' => ['id' => 99], 'text' => 'x', 'is_topic_message' => true]]));
echo "Offline webhook input/routing checks passed (no SDK or Telegram transport).\n";
