package main

import (
	"context"
	"errors"
	"log"
	"os"
	"os/signal"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("set TELEGRAM_BOT_TOKEN")
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()

	b, err := bot.New(token, bot.WithErrorsHandler(func(err error) {
		log.Printf("update receiver: %v", err)
	}))
	if err != nil {
		log.Fatal(err)
	}
	b.RegisterHandlerMatchFunc(func(u *models.Update) bool {
		return u.Message != nil && u.Message.Text != ""
	}, func(ctx context.Context, b *bot.Bot, u *models.Update) {
		_, err := b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: u.Message.Chat.ID,
			Text:   u.Message.Text,
		})
		if err != nil && !errors.Is(err, context.Canceled) {
			log.Printf("send message: %v", err)
		}
	})
	b.Start(ctx)
}
