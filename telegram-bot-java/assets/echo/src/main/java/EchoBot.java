import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.telegram.telegrambots.client.okhttp.OkHttpTelegramClient;
import org.telegram.telegrambots.longpolling.TelegramBotsLongPollingApplication;
import org.telegram.telegrambots.longpolling.util.DefaultLongPollingUpdateConsumer;
import org.telegram.telegrambots.meta.api.methods.send.SendMessage;
import org.telegram.telegrambots.meta.api.objects.Update;
import org.telegram.telegrambots.meta.exceptions.TelegramApiException;
import org.telegram.telegrambots.meta.generics.TelegramClient;

public final class EchoBot extends DefaultLongPollingUpdateConsumer {
    private final TelegramClient client;

    private EchoBot(String token) {
        this(new OkHttpTelegramClient(token));
    }

    EchoBot(TelegramClient client) {
        this.client = client;
    }

    @Override
    public void consume(Update update) {
        if (!update.hasMessage() || !update.getMessage().hasText()) {
            return;
        }
        Integer directTopic = null;
        if (update.getMessage().hasDirectMessagesTopic()) {
            Long topicId = update.getMessage().getDirectMessagesTopic().getTopicId();
            // 10.3.0 receives a Long but its SendMessage setter accepts Integer.
            if (topicId == null || topicId <= 0 || topicId > Integer.MAX_VALUE) {
                System.err.println("Direct-message topic exceeds this SDK request field; use a compatible adapter");
                return;
            }
            directTopic = topicId.intValue();
        }
        SendMessage reply = SendMessage.builder()
                .chatId(update.getMessage().getChatId())
                .text(update.getMessage().getText())
                .messageThreadId(Boolean.TRUE.equals(update.getMessage().getIsTopicMessage())
                        ? update.getMessage().getMessageThreadId() : null)
                .directMessagesTopicId(directTopic)
                .build();
        try {
            client.execute(reply);
        } catch (TelegramApiException e) {
            System.err.println("Could not deliver echo: " + e.getClass().getSimpleName());
        }
    }

    public static void main(String[] args) throws Exception {
        String token = System.getenv("TELEGRAM_BOT_TOKEN");
        if (token == null || token.isBlank()) {
            throw new IllegalArgumentException("Set TELEGRAM_BOT_TOKEN");
        }
        ScheduledExecutorService pollingExecutor = Executors.newSingleThreadScheduledExecutor();
        TelegramBotsLongPollingApplication application = new TelegramBotsLongPollingApplication(
                com.fasterxml.jackson.databind.ObjectMapper::new,
                new org.telegram.telegrambots.longpolling.util.TelegramOkHttpClientFactory.DefaultOkHttpClientCreator(),
                () -> pollingExecutor);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                application.close();
            } catch (Exception e) {
                System.err.println("Polling shutdown failed");
            } finally {
                pollingExecutor.shutdownNow();
            }
        }));
        try {
            application.registerBot(token, new EchoBot(token));
            new CountDownLatch(1).await();
        } finally {
            try {
                application.close();
            } finally {
                pollingExecutor.shutdownNow();
                pollingExecutor.awaitTermination(5, TimeUnit.SECONDS);
            }
        }
    }
}
