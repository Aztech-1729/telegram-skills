import static org.junit.jupiter.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.telegram.telegrambots.meta.api.methods.send.SendMessage;
import org.telegram.telegrambots.meta.api.objects.Update;
import org.telegram.telegrambots.meta.generics.TelegramClient;

class EchoBotTest {
    private final List<SendMessage> sends = new ArrayList<>();
    private final TelegramClient client = (TelegramClient) Proxy.newProxyInstance(
            TelegramClient.class.getClassLoader(), new Class<?>[]{TelegramClient.class},
            (proxy, method, args) -> {
                if (!method.getName().equals("execute") || !(args[0] instanceof SendMessage)) {
                    throw new AssertionError("Unexpected client operation: " + method.getName());
                }
                sends.add((SendMessage) args[0]);
                return null;
            });

    @Test
    void preservesTopicAndPlainTextWithoutNetwork() throws Exception {
        Update update = new ObjectMapper().readValue("""
            {"update_id":1,"message":{"message_id":2,"date":1,
             "chat":{"id":-1001234567890,"type":"supergroup","title":"Fixture"},
             "text":"<plain & text>","is_topic_message":true,"message_thread_id":42}}
            """, Update.class);
        try (EchoBot bot = new EchoBot(client)) { bot.consume(update); }
        assertEquals(1, sends.size());
        assertEquals("-1001234567890", sends.get(0).getChatId());
        assertEquals(42, sends.get(0).getMessageThreadId());
        assertEquals("<plain & text>", sends.get(0).getText());
        assertNull(sends.get(0).getParseMode());
    }

    @Test
    void preservesDirectMessageTopic() throws Exception {
        Update update = new ObjectMapper().readValue("""
            {"update_id":4,"message":{"message_id":2,"date":1,
             "chat":{"id":-1001234567890,"type":"supergroup","title":"Fixture"},
             "text":"Hello","direct_messages_topic":{"topic_id":42}}}
            """, Update.class);
        try (EchoBot bot = new EchoBot(client)) { bot.consume(update); }
        assertEquals(42, sends.get(0).getDirectMessagesTopicId());
        assertNull(sends.get(0).getMessageThreadId());
    }

    @Test
    void refusesAnUnrepresentableDirectTopicWithoutTruncation() throws Exception {
        Update update = new ObjectMapper().readValue("""
            {"update_id":5,"message":{"message_id":2,"date":1,
             "chat":{"id":-1001234567890,"type":"supergroup","title":"Fixture"},
             "text":"Hello","direct_messages_topic":{"topic_id":4294967296}}}
            """, Update.class);
        try (EchoBot bot = new EchoBot(client)) { bot.consume(update); }
        assertTrue(sends.isEmpty());
    }

    @Test
    void ignoresCallbackAndEditedMessageVariants() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        try (EchoBot bot = new EchoBot(client)) {
            bot.consume(mapper.readValue("""
                {"update_id":2,"callback_query":{"id":"fixture","chat_instance":"fixture-chat",
                 "data":"help","from":{"id":99,"is_bot":false,"first_name":"Fixture"}}}
                """, Update.class));
            bot.consume(mapper.readValue("""
                {"update_id":3,"edited_message":{"message_id":2,"date":1,
                 "chat":{"id":99,"type":"private"},"text":"Edited"}}
                """, Update.class));
        }
        assertTrue(sends.isEmpty());
    }
}
