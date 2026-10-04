package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

// The classic SDK logs transport errors internally, including during polling.
// Redact them before they enter the SDK: URL paths contain the bot credential.
type safeHTTPClient struct{ client *http.Client }
type hiddenTransportCause struct{ cause error }

func (e hiddenTransportCause) Error() string { return "transport request failed" }
func (e hiddenTransportCause) Unwrap() error { return e.cause }

func (c safeHTTPClient) Do(request *http.Request) (*http.Response, error) {
	response, err := c.client.Do(request)
	if err == nil {
		return response, nil
	}
	var requestError *url.Error
	if errors.As(err, &requestError) {
		redacted := *requestError
		redacted.URL = "[redacted]"
		redacted.Err = hiddenTransportCause{cause: requestError.Err}
		return response, &redacted
	}
	return response, hiddenTransportCause{cause: err}
}

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("set TELEGRAM_BOT_TOKEN")
	}
	b, err := tgbotapi.NewBotAPIWithClient(token, tgbotapi.APIEndpoint,
		safeHTTPClient{client: &http.Client{Timeout: 45 * time.Second}})
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
