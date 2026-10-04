package main

import (
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"testing"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

type offlineTransport func(*http.Request) (*http.Response, error)

func (f offlineTransport) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestTransportRedactsURLAndNestedMessagePreservingErrorIdentity(t *testing.T) {
	const token = "123456:offline-secret"
	cause := errors.New("fixture network failure")
	client := safeHTTPClient{client: &http.Client{Transport: offlineTransport(func(r *http.Request) (*http.Response, error) {
		return nil, fmt.Errorf("failure for %s: %w", r.URL, cause)
	})}}
	req, err := http.NewRequest(http.MethodPost, "https://api.telegram.org/bot"+token+"/getMe", nil)
	if err != nil {
		t.Fatal(err)
	}
	_, err = client.Do(req)
	if err == nil || strings.Contains(fmt.Sprintf("%+v", err), token) || !errors.Is(err, cause) {
		t.Fatalf("redaction or cause identity failed: %v", err)
	}
	var requestError *url.Error
	if !errors.As(err, &requestError) || requestError.URL != "[redacted]" {
		t.Fatal("request error type or redacted URL lost")
	}
}

func TestSDKStartupAndPollingCannotLogCredentialFromTransportError(t *testing.T) {
	const token = "123456:offline-secret"
	cause := errors.New("fixture network failure")
	for _, allowStartup := range []bool{false, true} {
		client := safeHTTPClient{client: &http.Client{Transport: offlineTransport(func(r *http.Request) (*http.Response, error) {
			if allowStartup && strings.HasSuffix(r.URL.Path, "/getMe") {
				return &http.Response{StatusCode: http.StatusOK, Header: make(http.Header),
					Body: io.NopCloser(strings.NewReader(`{"ok":true,"result":{"id":123456,"is_bot":true,"first_name":"Offline","username":"offline_bot"}}`))}, nil
			}
			return nil, fmt.Errorf("failure for %s: %w", r.URL, cause)
		})}}
		bot, err := tgbotapi.NewBotAPIWithClient(token, tgbotapi.APIEndpoint, client)
		if allowStartup {
			if err != nil {
				t.Fatal("synthetic startup failed")
			}
			_, err = bot.GetUpdates(tgbotapi.NewUpdate(0))
		}
		if err == nil || strings.Contains(err.Error(), token) || !errors.Is(err, cause) {
			t.Fatal("SDK transport error was not safely propagated")
		}
	}
}
