import java.util.concurrent.CountDownLatch;
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
        client = new OkHttpTelegramClient(token);
    }

    @Override
    public void consume(Update update) {
        if (!update.hasMessage() || !update.getMessage().hasText()) {
            return;
        }
        SendMessage reply = SendMessage.builder()
                .chatId(update.getMessage().getChatId())
                .text(update.getMessage().getText())
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
        TelegramBotsLongPollingApplication application = new TelegramBotsLongPollingApplication();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                application.close();
            } catch (Exception e) {
                System.err.println("Polling shutdown failed");
            }
        }));
        try {
            application.registerBot(token, new EchoBot(token));
            new CountDownLatch(1).await();
        } finally {
            application.close();
        }
    }
}
