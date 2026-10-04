package main

import (
	"bytes"
	"context"
	"errors"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"

	contribbolt "github.com/gotd/contrib/bbolt"
	"github.com/gotd/td/bin"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/telegram/updates"
	"github.com/gotd/td/tg"
	boltdb "go.etcd.io/bbolt"
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

func TestSessionAndRecoveryStateSurviveDatabaseReopen(t *testing.T) {
	ctx := context.Background()
	path := filepath.Join(t.TempDir(), "offline.db")
	open := func() *boltdb.DB {
		db, err := boltdb.Open(path, 0600, &boltdb.Options{Timeout: time.Second})
		if err != nil {
			t.Fatal(err)
		}
		return db
	}
	db := open()
	session := contribbolt.NewSessionStorage(db, "bot", []byte("sessions"))
	state := contribbolt.NewStateStorage(db)
	payload := []byte("offline session fixture, not an authorization key")
	expected := updates.State{Pts: 10, Qts: 2, Date: 123, Seq: 4}
	if err := session.StoreSession(ctx, payload); err != nil {
		t.Fatal(err)
	}
	if err := state.SetState(ctx, 123456, expected); err != nil {
		t.Fatal(err)
	}
	if err := state.SetChannelPts(ctx, 123456, 10, 33); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	db = open()
	defer db.Close()
	loaded, err := contribbolt.NewSessionStorage(db, "bot", []byte("sessions")).LoadSession(ctx)
	if err != nil || !bytes.Equal(loaded, payload) {
		t.Fatalf("session restore: %q, %v", loaded, err)
	}
	state = contribbolt.NewStateStorage(db)
	actual, found, err := state.GetState(ctx, 123456)
	if err != nil || !found || actual != expected {
		t.Fatalf("recovery state restore: %#v, %t, %v", actual, found, err)
	}
	if _, found, err := state.GetState(ctx, 42); err != nil || found {
		t.Fatalf("state leaked across account IDs: %t, %v", found, err)
	}
	pts, found, err := state.GetChannelPts(ctx, 123456, 10)
	if err != nil || !found || pts != 33 {
		t.Fatalf("channel pts restore: %d, %t, %v", pts, found, err)
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
