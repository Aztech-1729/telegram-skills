use teloxide::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    pretty_env_logger::init();
    let token = std::env::var("TELOXIDE_TOKEN")?;
    if token.trim().is_empty() {
        return Err("TELOXIDE_TOKEN is empty".into());
    }
    let bot = Bot::new(token);
    teloxide::repl(bot, |bot: Bot, message: Message| async move {
        if let Some(text) = message.text() {
            bot.send_message(message.chat.id, text).await?;
        }
        Ok(())
    })
    .await;
    Ok(())
}
