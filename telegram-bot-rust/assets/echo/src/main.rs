use teloxide::payloads::SendMessage;
use teloxide::prelude::*;
use teloxide::requests::JsonRequest;

fn echo_request(bot: &Bot, message: &Message) -> Option<JsonRequest<SendMessage>> {
    let text = message.text()?;
    let mut request = bot.send_message(message.chat.id, text);
    if message.is_topic_message {
        if let Some(thread_id) = message.thread_id {
            request = request.message_thread_id(thread_id);
        }
    }
    Some(request)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    pretty_env_logger::init();
    let token = std::env::var("TELOXIDE_TOKEN")?;
    if token.trim().is_empty() {
        return Err("TELOXIDE_TOKEN is empty".into());
    }
    let bot = Bot::new(token);
    teloxide::repl(bot, |bot: Bot, message: Message| async move {
        if let Some(request) = echo_request(&bot, &message) {
            request.await?;
        }
        Ok(())
    })
    .await;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use teloxide::requests::HasPayload;

    #[test]
    fn builds_plain_text_in_the_source_topic_without_sending() {
        let message: Message = serde_json::from_value(serde_json::json!({
            "message_id": 2, "date": 1,
            "chat": {"id": -1001234567890_i64, "type": "supergroup", "title": "Fixture"},
            "text": "<plain & text>", "is_topic_message": true, "message_thread_id": 42
        }))
        .unwrap();
        let request = echo_request(&Bot::new("123456:synthetic-offline-token"), &message).unwrap();
        let payload = serde_json::to_value(request.payload_ref()).unwrap();
        assert_eq!(payload["chat_id"], -1001234567890_i64);
        assert_eq!(payload["message_thread_id"], 42);
        assert_eq!(payload["text"], "<plain & text>");
        assert!(payload.get("parse_mode").is_none());
    }

    #[test]
    fn ignores_non_text_and_leaves_non_topic_routing_unset() {
        let mut value = serde_json::json!({"message_id": 2, "date": 1,
            "chat": {"id": 99, "type": "private"},
            "photo": [{"file_id": "fixture", "file_unique_id": "fixture", "width": 1, "height": 1}]});
        let bot = Bot::new("123456:synthetic-offline-token");
        let message: Message = serde_json::from_value(value.clone()).unwrap();
        assert!(echo_request(&bot, &message).is_none());
        value.as_object_mut().unwrap().remove("photo");
        value["text"] = "Hello".into();
        let message: Message = serde_json::from_value(value).unwrap();
        let request = echo_request(&bot, &message).unwrap();
        assert!(request.payload_ref().message_thread_id.is_none());
    }
}
