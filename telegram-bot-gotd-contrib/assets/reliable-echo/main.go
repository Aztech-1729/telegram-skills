package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"time"

	contribbolt "github.com/gotd/contrib/bbolt"
	"github.com/gotd/contrib/middleware/floodwait"
	"github.com/gotd/contrib/middleware/ratelimit"
	"github.com/gotd/contrib/storage"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/telegram/updates"
	"github.com/gotd/td/tg"
	boltdb "go.etcd.io/bbolt"
	"golang.org/x/time/rate"
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
	db, err := boltdb.Open("bot.db", 0600, &boltdb.Options{Timeout: time.Second})
	if err != nil {
		return err
	}
	defer db.Close()

	dispatcher := tg.NewUpdateDispatcher()
	gaps := updates.New(updates.Config{
		Handler: dispatcher,
		Storage: contribbolt.NewStateStorage(db),
	})
	peerStore := contribbolt.NewPeerStorage(db, []byte("peers"))
	waiter := floodwait.NewWaiter().WithMaxRetries(3).WithMaxWait(time.Minute)
	client := telegram.NewClient(appID, appHash, telegram.Options{
		SessionStorage: contribbolt.NewSessionStorage(db, "bot", []byte("sessions")),
		UpdateHandler:  storage.UpdateHook(gaps, peerStore),
		Middlewares: []telegram.Middleware{
			waiter,
			ratelimit.New(rate.Every(200*time.Millisecond), 2),
		},
	})
	sender := message.NewSender(client.API())
	dispatcher.OnNewMessage(func(ctx context.Context, e tg.Entities, u *tg.UpdateNewMessage) error {
		m, ok := u.Message.(*tg.Message)
		if !ok || m.Out || m.Message == "" {
			return nil
		}
		_, err := sender.Reply(e, u).Text(ctx, m.Message)
		return err
	})
	return waiter.Run(ctx, func(ctx context.Context) error {
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
			return gaps.Run(ctx, client.API(), self.ID, updates.AuthOptions{IsBot: true})
		})
	})
}

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	if err := run(ctx); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatal(err)
	}
}
