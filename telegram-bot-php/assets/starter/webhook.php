<?php
declare(strict_types=1);
require __DIR__ . '/vendor/autoload.php';

use Telegram\Bot\Api;

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    exit;
}
$token = getenv('TELEGRAM_BOT_TOKEN');
$secret = getenv('TELEGRAM_WEBHOOK_SECRET');
if (!$token || !$secret) {
    http_response_code(503);
    exit;
}
$supplied = $_SERVER['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] ?? '';
if (!hash_equals($secret, $supplied)) {
    http_response_code(403);
    exit;
}
$raw = file_get_contents('php://input', false, null, 0, 524289);
if ($raw === false || strlen($raw) > 524288) {
    http_response_code(413);
    exit;
}
try {
    $payload = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
    if (!is_array($payload) || !isset($payload['update_id']) || !is_int($payload['update_id'])) {
        http_response_code(400);
        exit;
    }
    // Deliberately echo only ordinary text messages, not edited/business/callback updates.
    $message = $payload['message'] ?? null;
    if (is_array($message) && isset($message['chat']['id'], $message['text']) && is_string($message['text'])) {
        $telegram = new Api($token);
        $telegram->sendMessage(['chat_id' => $message['chat']['id'], 'text' => $message['text']]);
    }
    http_response_code(200);
} catch (JsonException $error) {
    http_response_code(400);
} catch (Throwable $error) {
    error_log('Telegram webhook failure: ' . get_class($error));
    http_response_code(503);
}
