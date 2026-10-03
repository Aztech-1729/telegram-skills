package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"

	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/tg"
)

func run(ctx context.Context) error {
	appID, err := strconv.Atoi(os.Getenv("APP_ID"))
	if err != nil || appID <= 0 {
		return fmt.Errorf("set APP_ID to a positive integer")
	}
	appHash, token := os.Getenv("APP_HASH"), os.Getenv("BOT_TOKEN")
	if appHash == "" || token == "" {
		return fmt.Errorf("set APP_HASH and BOT_TOKEN")
	}
	path := os.Getenv("SESSION_FILE")
	if path == "" {
		path = "session.json"
	}
	dispatcher := tg.NewUpdateDispatcher()
	client := telegram.NewClient(appID, appHash, telegram.Options{
		SessionStorage: &session.FileStorage{Path: path},
		UpdateHandler:  dispatcher,
	})
	sender := message.NewSender(client.API())
	dispatcher.OnNewMessage(func(ctx context.Context, entities tg.Entities, u *tg.UpdateNewMessage) error {
		m, ok := u.Message.(*tg.Message)
		if !ok || m.Out || m.Message == "" {
			return nil
		}
		_, err := sender.Reply(entities, u).Text(ctx, m.Message)
		return err
	})
	return client.Run(ctx, func(ctx context.Context) error {
		status, err := client.Auth().Status(ctx)
		if err != nil {
			return err
		}
		if !status.Authorized {
			if _, err := client.Auth().Bot(ctx, token); err != nil {
				return err
			}
		}
		<-ctx.Done()
		return ctx.Err()
	})
}

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	if err := run(ctx); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatal(err)
	}
}
