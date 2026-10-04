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
	var ready atomic.Bool
	client := telegram.NewClient(appID, appHash, telegram.Options{
		SessionStorage: contribbolt.NewSessionStorage(db, "bot", []byte("sessions")),
		UpdateHandler:  verifiedUpdates(&ready, storage.UpdateHook(gaps, peerStore)),
		Middlewares: []telegram.Middleware{
			waiter,
			ratelimit.New(rate.Every(200*time.Millisecond), 2),
		},
	})
	sender := message.NewSender(client.API())
	dispatcher.OnNewMessage(echoHandler(&ready, sender))
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
			if err := checkBotIdentity(self, botID); err != nil {
				return err
			}
			ready.Store(true)
			defer ready.Store(false)
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
