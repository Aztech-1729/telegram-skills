package main

import (
	"log"
	"os"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers/filters/message"
)

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("set TELEGRAM_BOT_TOKEN")
	}
	b, err := gotgbot.NewBot(token, nil)
	if err != nil {
		log.Fatal(err)
	}
	dispatcher := ext.NewDispatcher(&ext.DispatcherOpts{
		MaxRoutines: 8,
		Error: func(_ *gotgbot.Bot, _ *ext.Context, err error) ext.DispatcherAction {
			log.Printf("handler: %v", err)
			return ext.DispatcherActionNoop
		},
	})
	dispatcher.AddHandler(handlers.NewMessage(message.Text,
		func(b *gotgbot.Bot, ctx *ext.Context) error {
			_, err := ctx.EffectiveMessage.Reply(b, ctx.EffectiveMessage.Text, nil)
			return err
		}))
	updater := ext.NewUpdater(dispatcher, nil)
	if err := updater.StartPolling(b, &ext.PollingOpts{}); err != nil {
		log.Fatal(err)
	}
	updater.Idle()
}
