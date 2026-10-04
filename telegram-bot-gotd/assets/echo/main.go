package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync/atomic"

	"github.com/gotd/td/session"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/tg"
)

func expectedBotID(token string) (int64, error) {
	prefix, secret, ok := strings.Cut(token, ":")
	id, err := strconv.ParseInt(prefix, 10, 64)
	if !ok || err != nil || id <= 0 || secret == "" {
		return 0, fmt.Errorf("BOT_TOKEN must have a positive bot ID and secret")
	}
	return id, nil
}

func checkBotIdentity(self *tg.User, expectedID int64) error {
	if self == nil || !self.Bot || self.ID != expectedID {
		return fmt.Errorf("authorized session does not match the requested bot")
	}
	return nil
}

func verifiedUpdates(ready *atomic.Bool, next telegram.UpdateHandler) telegram.UpdateHandler {
	return telegram.UpdateHandlerFunc(func(ctx context.Context, update tg.UpdatesClass) error {
		if !ready.Load() {
			return nil
		}
		return next.Handle(ctx, update)
	})
}

func echoHandler(ready *atomic.Bool, sender *message.Sender) tg.NewMessageHandler {
	return func(ctx context.Context, entities tg.Entities, u *tg.UpdateNewMessage) error {
		// Updates can arrive during session initialization, before identity is checked.
		if !ready.Load() {
			return nil
		}
		m, ok := u.Message.(*tg.Message)
		if !ok || m.Out || m.Message == "" {
			return nil
		}
		_, err := sender.Reply(entities, u).Text(ctx, m.Message)
		return err
	}
}

func run(ctx context.Context) error {
	appID, err := strconv.Atoi(os.Getenv("APP_ID"))
	if err != nil || appID <= 0 {
		return fmt.Errorf("set APP_ID to a positive integer")
	}
	appHash, token := os.Getenv("APP_HASH"), os.Getenv("BOT_TOKEN")
	if appHash == "" || token == "" {
		return fmt.Errorf("set APP_HASH and BOT_TOKEN")
	}
	botID, err := expectedBotID(token)
	if err != nil {
		return err
	}
	path := os.Getenv("SESSION_FILE")
	if path == "" {
		path = "session.json"
	}
	dispatcher := tg.NewUpdateDispatcher()
	var ready atomic.Bool
	client := telegram.NewClient(appID, appHash, telegram.Options{
		SessionStorage: &session.FileStorage{Path: path},
		UpdateHandler:  verifiedUpdates(&ready, dispatcher),
	})
	sender := message.NewSender(client.API())
	dispatcher.OnNewMessage(echoHandler(&ready, sender))
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
		self, err := client.Self(ctx)
		if err != nil {
			return err
		}
		if err := checkBotIdentity(self, botID); err != nil {
			return err
		}
		ready.Store(true)
		defer ready.Store(false)
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
