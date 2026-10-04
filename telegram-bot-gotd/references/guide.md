# gotd/td: MTProto implementation reference

Checked on **2026-10-03** against gotd/td **v0.162.0**, with Go **1.25.0** in its module directive. See [sources.md](sources.md).

## Contents

Protocol selection; setup and bot lifecycle; user/QR authentication; update dispatch and recovery; sessions and peers; message/media helpers; raw RPCs; connection options; wrappers; verification; failure diagnosis and interaction feedback.

## 1. Select MTProto for a concrete requirement

gotd/td is a Go MTProto client for authorized user or bot accounts, with generated TL types in tg and higher-level helpers. Use it for account operations or protocol capabilities the HTTP Bot API does not expose.

An ordinary HTTP bot usually fits the Go Bot API skill. MTProto has a different schema, ID/peer representation, update model, and set of bot restrictions. It is not a promise of greater throughput, unrestricted history, TDLib equivalence, unlimited files, or freedom from flood limits.

For large-file requirements compare the official local HTTP Bot API server with MTProto. Both remain subject to their actual file/account rules.

## 2. Configure credentials and session

Obtain application api_id/api_hash from my.telegram.org; configure APP_ID/APP_HASH. Bot accounts also require BOT_TOKEN. User accounts authenticate through a phone/code/password or supported QR flow.

```bash
go get github.com/gotd/td@v0.162.0
```

Keep the session file or database outside source control, with account-specific paths and restrictive filesystem/backup access. Application credentials, bot tokens and MTProto authorization keys are different secrets. Session persistence avoids unnecessary new authorization; it does not persist business data or update history.

## 3. Bot lifecycle and original echo

[The complete starter](../assets/echo/main.go) uses:

- telegram.NewClient with a tg.UpdateDispatcher assigned to Options.UpdateHandler.
- Core `session.FileStorage{Path: ...}`; the former `contrib/storage.FileSession` example was not the correct API.
- A sender constructed from client.API(), captured in handlers.
- Auth().Status followed by Auth().Bot only when authorization is absent.
- Self's bot flag and ID checked against the token before the update chain is enabled.
- A Run callback that stays alive until cancellation.

Build from [its module](../assets/echo/go.mod) with `go build .`, and run `go test ./...` for [offline identity/handler checks](../assets/echo/main_test.go). Set APP_ID, APP_HASH, BOT_TOKEN and optionally SESSION_FILE before deliberately running it. An authorized saved session is reused even if a different token is supplied. The starter refuses a user or different bot; changing tokens does not switch the file's account. Select another account-specific session path or handle an intentional account change through the application's authentication flow.

The ready gate drops incoming updates before identity verification and after shutdown; it avoids effects from the wrong restored account, but is not a durable startup buffer. This plain dispatcher starter does not recover those updates. For loss-sensitive applications, integrate the recovery manager/durable inbox after identity verification and test its startup/reconnect boundary.

The starter handles incoming ordinary text messages, including basic-group messages, and ignores outgoing/media-only messages. It does not claim to process supergroup/channel updates or notify administrators.

client.Run establishes the connection and invokes its callback; manual client construction does not automatically perform the application's bot/user auth flow. Returning from the callback ends that run. The environment helpers can perform additional setup, but their behavior and callback options must be read at the selected version.

## 4. User and QR authentication

For a user account, use telegram/auth.NewFlow with a UserAuthenticator and SendCodeOptions, then Auth().IfNecessary inside client.Run. The authenticator supplies phone/code, 2FA password where required, and handles sign-up/terms when applicable.

For interactive programs, gotd/contrib/auth/terminal provides a verified implementation. For services, design a controlled authentication UI rather than forwarding login codes into arbitrary bot chats. CodeOnly does not implement a complete password-required flow.

client.QR() exposes telegram/auth/qrlogin helpers. QR login requires expiry/refresh handling and acceptance by an already logged-in Telegram client. Use the official QR example and listen for login-token updates as its flow requires; displaying a static link is not a complete login implementation.

If an authorized session is revoked, surface reauthentication as an explicit state. Do not loop indefinitely through fresh phone/bot logins. Telegram's account restrictions and anti-spam rules still apply; read the project's account guidance before automating a user account.

## 5. Typed update dispatch

Register typed methods from `tg.NewUpdateDispatcher()`:

| Event | Dispatcher method |
| --- | --- |
| Ordinary/private/basic-group message | OnNewMessage |
| Supergroup/channel message | OnNewChannelMessage |
| Edited ordinary/channel message | OnEditMessage / OnEditChannelMessage |
| Deleted message | OnDeleteMessages |
| Bot callback | OnBotCallbackQuery |
| Bot inline query | OnBotInlineQuery |

The earlier OnChannelPost/OnInlineQuery names mixed HTTP framework conventions with gotd's generated names. Check the generated dispatcher for other update constructors.

An event's Message is an interface: test for *tg.Message before accessing its text, peer, or outgoing flag. tg.Entities contains the users/chats accompanying that update. It can help reconstruct input peers; do not assume every referenced user is always present.

Use predicates in the handler or a documented wrapper for commands/filters. tg.UpdateDispatcher is not a complete HTTP-style command/FSM framework.

Handlers return errors, but arbitrary business handlers are not guaranteed to retry safely or persist their effect. Log/report failures through the selected handler/manager design and make business effects idempotent.

## 6. Gap recovery is a separate engine

For offline/reconnection recovery, create:

```go
gaps := updates.New(updates.Config{Handler: dispatcher})
```

Assign gaps to Options.UpdateHandler. After auth, fetch client.Self and run `gaps.Run(ctx, client.API(), self.ID, updates.AuthOptions{IsBot: true})` inside the client callback for a bot. For a user, configure IsBot appropriately.

Constructing the manager without calling Run only forwards updates; it does not activate recovery. The old Options.Updates/NewConfig/NewState sketch was not verified against this release.

Defaults use memory for StateStorage and access-hash stores. Persist the state and channel/user access hashes needed for restart recovery. Missing/expired state and difference-too-long responses can still require reconciliation; no manager guarantees unlimited offline history.

When raw outgoing RPCs return updates, consider telegram/updates/hook.UpdateHook. Operations returning affectedMessages/affectedHistory need the matching AffectedHook to keep local pts synchronized. Read the current updates example before adding those hooks. Application inbox/outbox records are still separate from protocol recovery state.

Use the contrib guide for concrete storage wiring.

## 7. Sessions, migration, and peers

Core session.Storage exposes LoadSession/StoreSession; a custom database implementation must obey its not-found and synchronization contract. session.FileStorage is appropriate for a single local client.

session.TelethonSession imports a Telethon string session, while session.TDesktopSession converts an account already parsed from Telegram Desktop data. These are migration tools for the same authorized account, not methods to acquire other accounts' access.

An MTProto peer often requires both an ID and access hash. A Bot API chat_id is not interchangeable with tg.InputPeerClass. For a known typed input peer use sender.To(peer); for a username/domain use sender.Resolve or ResolveDomain. Keep peer data scoped to the authorized account.

The contrib storage.UpdateHook and ResolverCache capture and reuse resolved peers. A cache can become stale or incomplete, and deleted/inaccessible users/channels require normal error handling. Do not construct an arbitrary user's access hash from a numeric ID.

## 8. Message builders and interactions

message.NewSender(client.API()) supplies a convenient layer over raw RPCs. At the checked version:

- `sender.Reply(entities, update).Text(ctx, text)` replies using the event and entities.
- `sender.Resolve("@username").Text(ctx, text)` resolves a target before sending.
- `sender.To(inputPeer).Text(ctx, text)` sends to an existing typed peer.
- `sender.Self()` targets Saved Messages for a suitable user account.

ResolveDomain returns a request builder, not the old sketch's resolved peer/error pair. The starter demonstrates the verified reply signature.

Markup uses generated tg reply-markup objects and Builder.Row/Markup. Distinguish sending a reply from answering a bot callback: the latter uses the appropriate messages.setBotCallbackAnswer RPC. Inline queries use their own update and result types.

For styled content use message/styling or explicit entities and escaping. Albums/media use message builders and generated input-media types; check flags and return errors for the exact media type.

## 9. Uploads and downloads

uploader.NewUploader(raw).FromPath/FromReader returns an input file for a subsequent media operation. UploadedPhoto/UploadedDocument builders describe the media; an upload alone does not send a message.

downloader.NewDownloader().Download(raw, location).ToPath downloads a typed file location. CDN redirects, progress, cancellation and concurrency are helper capabilities; the access-controlled file location and permitted size still need to be correct.

Bound upload/download workers and disk use. Keep files open while the helper reads them, clean temporary files after completion, and handle file-reference expiration through a supported refresh path.

Use the checked bot-upload/save-media/bot-bigbuckbunny examples for full flows, rather than the previous message.Upload/UploadedPhotoUploader placeholders.

## 10. Raw generated RPCs

client.API() exposes a *tg.Client. Generated method names such as MessagesGetHistory or ChannelsCreateChannel mirror TL constructors; read their generated/official documentation for required account type and permissions.

Sending methods often require a random_id. Prefer the message helper unless raw control is necessary; if retrying the same raw send, preserve the operation's intended random_id rather than generating a new independent effect.

Use pagination helpers in telegram/query for history/dialogs/participants instead of assuming one request returns a full collection. History may be restricted for bot accounts and inaccessible chats.

## 11. Connection options and pooling

telegram.Options includes Resolver, Device, middleware, session and update-handler configuration. Read the exact type at the chosen tag; the former DeviceConfig field sketch should not be pasted blindly.

telegram/dcs supplies DC and MTProxy resolution; proxy secrets/transports have separate setup rules. Desktop-like device/resolver helpers configure protocol metadata and transport, but do not guarantee an account will avoid restrictions.

client.Pool(max) belongs to gotd/td and returns a CloseInvoker; close it and use tg.NewClient(pool) for RPC/upload work. It is not a contrib/pool package, nor a multi-account authentication manager. Isolate separate accounts' clients and sessions.

## 12. Higher-level alternatives

gotd/contrib supplies optional infrastructure. gotd/botapi exposes a Bot API-shaped interface over MTProto; review its current implemented surface, storage and transport rather than treating it as an HTTP drop-in or limit bypass.

GoTGProto is a wrapper with its own helpers and storage conventions. The former pageton/gotg repository is archived and points to mtgo-labs/mtgo. Evaluate the successor as its own framework; do not assume its imports, generated types, middleware or storage adapters are identical to gotd.

## 13. Verification

Build the pinned application without starting it. Unit-test command predicates and business effects using typed updates, fixtures or a fake invoker. Integration-test session restore, gap recovery, permissions, transfers and proxy behavior only in an authorized test environment.

Report the actual validation. A compile check neither authenticates an account nor verifies real-server reconnect, loss recovery or media limits.

## 14. Failure diagnosis and interaction feedback

| Symptom | Inspect first | Fix or prove |
| --- | --- | --- |
| Unexpected account handles updates | Restored Self ID/type and session path | Verify intended identity before dispatch, stores or sends; do not silently replace an authorized session |
| Reply reports `chat/user not found` | tg.Entities supplied with the event | sender.Reply extracts a typed peer from those entities; a numeric ID alone is insufficient |
| Channel messages never arrive at the handler | OnNewMessage versus OnNewChannelMessage | Handle the intended generated update constructor and verify membership/rights |
| Updates disappear across a restart | Manager.Run, StateStorage/access-hash stores and gap callbacks | Session restore supplies authorization; separately prove the needed recovery behavior |
| A send returns an error after a business write | Committed operation record, random_id and outbound response | Preserve the intended operation identity; reconcile ambiguity rather than repeating fulfillment |
| A Run callback exits immediately | Callback lifetime/owned worker supervision | Returning ends the connection run; keep the intended service lifetime explicit |

The offline reply test supplies a basic group's actual entity along with its message, verifies the outgoing peer/text through a fake invoker, and preserves its returned error. Test private/channel peers with suitable fixtures when those routes are implemented; do not fabricate access hashes.

For a bot interface, answer bot callbacks with the corresponding generated RPC before slow work, authorize the actor, then describe the actual result in the message. Long transfers need paced progress and cancellation; a queued/deferred action should say so instead of claiming completion. Keep login code/password and QR expiry handling in the authorized user application's own flow. Use [bot UX](../../telegram-bot-ux/SKILL.md) and [accessibility](../../telegram-bot-accessibility/SKILL.md) when designing chat interactions. Add [Mini App design](../../telegram-bot-miniapp-design/SKILL.md) and [Mini App security](../../telegram-bot-miniapps/SKILL.md) only for a separate web surface; an MTProto session is not a launch-data validator.
