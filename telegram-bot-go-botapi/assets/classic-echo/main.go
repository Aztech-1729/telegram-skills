package main

import (
	"context"
	"log"
	"os"
	"os/signal"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("set TELEGRAM_BOT_TOKEN")
	}
	b, err := tgbotapi.NewBotAPI(token)
	if err != nil {
		log.Fatal(err)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	config := tgbotapi.NewUpdate(0)
	config.Timeout = 30
	updates := b.GetUpdatesChan(config)
	defer b.StopReceivingUpdates()
	for {
		select {
		case <-ctx.Done():
			return
		case u, ok := <-updates:
			if !ok {
				return
			}
			if u.Message == nil || u.Message.Text == "" {
				continue
			}
			msg := tgbotapi.NewMessage(u.Message.Chat.ID, u.Message.Text)
			if _, err := b.Send(msg); err != nil {
				log.Printf("send message: %v", err)
			}
		}
	}
}
