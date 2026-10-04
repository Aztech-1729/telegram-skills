<?php
declare(strict_types=1);
require __DIR__ . '/WebhookInput.php';

use Telegram\Bot\Api;
use TelegramStarter\IngressError;
use function TelegramStarter\decodeWebhook;
use function TelegramStarter\echoRequest;

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
    $payload = decodeWebhook($_SERVER['REQUEST_METHOD'], $secret, $supplied, $raw);
    $request = echoRequest($payload);
    if ($request !== null) {
        require __DIR__ . '/vendor/autoload.php';
        $telegram = new Api($token);
        $telegram->sendMessage($request);
    }
    http_response_code(200);
} catch (IngressError $error) {
    http_response_code($error->status);
} catch (Throwable $error) {
    error_log('Telegram webhook failure: ' . get_class($error));
    http_response_code(503);
}
