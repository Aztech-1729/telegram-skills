package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

// This checks the pinned SDK's receiver, using no Bot API requests or polling.
// In particular, SDK rejection is NOT an HTTP 4xx response in v1.27.0.
func TestWebhookReceiverBoundaries(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	updates := make(chan *models.Update, 1)
	errorsSeen := make(chan error, 4)
	b, err := bot.New("123456:offline-placeholder", bot.WithSkipGetMe(),
		bot.WithWebhookSecretToken("offline-secret"), bot.WithNotAsyncHandlers(),
		bot.WithErrorsHandler(func(err error) { errorsSeen <- err }),
		bot.WithDefaultHandler(func(_ context.Context, _ *bot.Bot, update *models.Update) { updates <- update }))
	if err != nil {
		t.Fatal(err)
	}
	done := make(chan struct{})
	go func() { b.StartWebhook(ctx); close(done) }()
	t.Cleanup(func() {
		cancel()
		select {
		case <-done:
		case <-time.After(time.Second):
			t.Error("webhook workers did not stop")
		}
	})
	for _, tc := range []struct{ name, secret, body string }{
		{"missing secret", "", `{"update_id":1}`},
		{"wrong secret", "wrong", `{"update_id":1}`},
		{"malformed JSON", "offline-secret", `{invalid`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/updates", strings.NewReader(tc.body))
			req.Header.Set("X-Telegram-Bot-Api-Secret-Token", tc.secret)
			response := httptest.NewRecorder()
			b.WebhookHandler().ServeHTTP(response, req)
			if response.Code != http.StatusOK {
				t.Fatalf("SDK response policy changed: got %d; recheck deployment guidance", response.Code)
			}
			select {
			case <-errorsSeen:
			default:
				t.Fatal("invalid request did not reach error hook")
			}
			select {
			case <-updates:
				t.Fatal("invalid request reached the business handler")
			default:
			}
		})
	}
	req := httptest.NewRequest(http.MethodPost, "/updates", strings.NewReader(`{"update_id":2,"message":{"message_id":3,"date":1,"chat":{"id":10,"type":"private"},"text":"hello"}}`))
	req.Header.Set("X-Telegram-Bot-Api-Secret-Token", "offline-secret")
	b.WebhookHandler().ServeHTTP(httptest.NewRecorder(), req)
	select {
	case update := <-updates:
		if update.ID != 2 || update.Message == nil || update.Message.Text != "hello" {
			t.Fatalf("incorrect decoded update: %#v", update)
		}
	case <-time.After(time.Second):
		t.Fatal("accepted update did not reach the handler")
	}
}

func TestCommandEntityMatchingRequiresExplicitMentionPolicy(t *testing.T) {
	selected := ""
	b, err := bot.New("123456:offline-placeholder", bot.WithSkipGetMe(), bot.WithNotAsyncHandlers(),
		bot.WithDefaultHandler(func(context.Context, *bot.Bot, *models.Update) { selected = "fallback" }))
	if err != nil {
		t.Fatal(err)
	}
	b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly,
		func(context.Context, *bot.Bot, *models.Update) { selected = "start" })
	for _, tc := range []struct {
		text, want string
		length     int
	}{
		{"/start details", "start", 6},
		{"/start@ExampleBot details", "fallback", 17},
	} {
		b.ProcessUpdate(context.Background(), &models.Update{Message: &models.Message{
			Text: tc.text, Entities: []models.MessageEntity{{Type: models.MessageEntityTypeBotCommand, Offset: 0, Length: tc.length}},
		}})
		if selected != tc.want {
			t.Fatalf("command %q selected %q, want %q", tc.text, selected, tc.want)
		}
	}
	b.RegisterHandler(bot.HandlerTypeMessageText, "start@ExampleBot", bot.MatchTypeCommandStartOnly,
		func(context.Context, *bot.Bot, *models.Update) { selected = "mentioned" })
	b.ProcessUpdate(context.Background(), &models.Update{Message: &models.Message{
		Text: "/start@ExampleBot details", Entities: []models.MessageEntity{{Type: models.MessageEntityTypeBotCommand, Offset: 0, Length: 17}},
	}})
	if selected != "mentioned" {
		t.Fatalf("explicit mention route selected %q", selected)
	}
}
