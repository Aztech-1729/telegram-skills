package main

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"

	"github.com/gotd/td/bin"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/tg"
)

func TestSavedSessionIdentity(t *testing.T) {
	id, err := expectedBotID("123456:offline-placeholder")
	if err != nil || id != 123456 {
		t.Fatalf("parse bot ID: %d, %v", id, err)
	}
	for _, token := range []string{"", "0:secret", "-1:secret", "123456:", "not-a-token", "999999999999999999999999:secret"} {
		if _, err := expectedBotID(token); err == nil {
			t.Fatalf("accepted malformed token %q", token)
		}
	}
	if err := checkBotIdentity(&tg.User{ID: id, Bot: true}, id); err != nil {
		t.Fatal(err)
	}
	for _, self := range []*tg.User{nil, {ID: id}, {ID: 42, Bot: true}} {
		if err := checkBotIdentity(self, id); err == nil {
			t.Fatal("accepted a missing, user, or different bot session")
		}
	}
}

var errOffline = errors.New("offline invoker stopped send")

type recordingInvoker struct {
	requests []bin.Encoder
}

func (i *recordingInvoker) Invoke(_ context.Context, request bin.Encoder, _ bin.Decoder) error {
	i.requests = append(i.requests, request)
	return errOffline
}

func TestNoEffectsBeforeIdentityAndCorrectReplyAfterReadiness(t *testing.T) {
	var ready atomic.Bool
	invoker := &recordingInvoker{}
	handler := echoHandler(&ready, message.NewSender(tg.NewClient(invoker)))
	update := &tg.UpdateNewMessage{Message: &tg.Message{
		ID: 7, PeerID: &tg.PeerChat{ChatID: 10}, Message: "hello",
	}}
	entities := tg.Entities{Chats: map[int64]*tg.Chat{10: {ID: 10}}}
	if err := handler(context.Background(), tg.Entities{}, update); err != nil || len(invoker.requests) != 0 {
		t.Fatalf("update had an effect before identity verification: %v", err)
	}
	ready.Store(true)
	for _, ignored := range []tg.MessageClass{&tg.MessageEmpty{}, &tg.Message{Out: true, Message: "outgoing"}, &tg.Message{}} {
		if err := handler(context.Background(), tg.Entities{}, &tg.UpdateNewMessage{Message: ignored}); err != nil {
			t.Fatal(err)
		}
	}
	if len(invoker.requests) != 0 {
		t.Fatal("echoed an outgoing, service, or empty message")
	}
	if err := handler(context.Background(), entities, update); !errors.Is(err, errOffline) {
		t.Fatalf("send error was lost: %v", err)
	}
	if len(invoker.requests) != 1 {
		t.Fatalf("expected one outgoing RPC, got %d", len(invoker.requests))
	}
	request, ok := invoker.requests[0].(*tg.MessagesSendMessageRequest)
	if !ok || request.Message != "hello" {
		t.Fatalf("unexpected outgoing request: %#v", invoker.requests[0])
	}
	peer, ok := request.Peer.(*tg.InputPeerChat)
	if !ok || peer.ChatID != 10 {
		t.Fatalf("reply selected wrong peer: %#v", request.Peer)
	}
	ready.Store(false)
	if err := handler(context.Background(), tg.Entities{}, update); err != nil || len(invoker.requests) != 1 {
		t.Fatal("handled an update after shutdown readiness was revoked")
	}
}

func TestVerifiedUpdatesGatesWholeHandlerChain(t *testing.T) {
	var ready atomic.Bool
	calls := 0
	next := telegram.UpdateHandlerFunc(func(context.Context, tg.UpdatesClass) error {
		calls++
		return errOffline
	})
	handler := verifiedUpdates(&ready, next)
	if err := handler.Handle(context.Background(), &tg.Updates{}); err != nil || calls != 0 {
		t.Fatal("unverified updates reached handler/store chain")
	}
	ready.Store(true)
	if err := handler.Handle(context.Background(), &tg.Updates{}); !errors.Is(err, errOffline) || calls != 1 {
		t.Fatalf("verified update forwarding/error propagation failed: %v", err)
	}
}
