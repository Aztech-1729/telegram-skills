# Rust teloxide: implementation reference

Checked **2026-10-03**. The starter pins published **teloxide 0.17.0**. See [sources.md](sources.md) for release-versus-development scope.

## Contents

Compatibility and features; original echo; Dispatcher and commands; dialogues/dependencies; callbacks/media; error handling; webhooks; async/state; verification.

## 1. Select the published API surface

teloxide is an async Rust HTTP Bot API framework over teloxide-core, Tokio and dptree. It supplies typed requests, combinable update filters, command macros, dialogue storage integrations, listeners and request adaptors.

The published 0.17.0 changelog includes Bot API 9.1; the checked development branch lists 9.2 under unreleased. Telegram's Bot API 10.3 is a separate server release. Do not assume Rich Messages, native draft requests or new button styling exist in published teloxide because they exist in Telegram's documentation.

The published crate metadata declares Rust 1.82. The checked development README asks for 1.85. Application dependency resolution may impose higher requirements; use a supported Rust toolchain, commit Cargo.lock for applications, and record the actual cargo check result.

For MTProto user accounts, select a different library after evaluating that protocol; teloxide is not a user-account client.

## 2. Dependency/features decision

[The original asset](../assets/echo/Cargo.toml) pins teloxide = "=0.17.0" and enables Tokio's multithread runtime and macros. It uses default teloxide features for TLS and Ctrl-C handling.

Add features only for the needed task:

| Need | Feature at 0.17.0 |
| --- | --- |
| BotCommands derive | macros |
| Axum webhook listener | webhooks-axum |
| Request throttling adaptor | throttle |
| SQLite dialogue storage | sqlite-storage-nativetls or sqlite-storage-rustls |
| PostgreSQL dialogue storage | postgres-storage-nativetls or postgres-storage-rustls |
| Redis dialogue storage | redis-storage |

Check TLS/backend dependency compatibility rather than enabling full by default. Do not use development-branch feature spelling without checking the published crate.

## 3. Original echo and REPL boundary

[assets/echo/src/main.rs](../assets/echo/src/main.rs) reads TELOXIDE_TOKEN, rejects an empty token, and uses repl for plain-text echoes. It ignores non-text messages. pretty_env_logger/log supplies local logging.

Copy the whole asset directory into an application location. `cargo check` verifies code/types without starting reception. `cargo run` deliberately starts a real Telegram receiver after TELOXIDE_TOKEN is set.

A REPL is useful for a simple message endpoint. For callbacks, multiple update variants, dependencies, dialogues, custom errors or shutdown, use Dispatcher. Do not run a REPL alongside a Dispatcher/second listener for the same token.

This repository update had no Rust toolchain available; the asset was reviewed against published API documentation, not compiled. Run cargo check before using it.

## 4. Dispatcher and typed commands

The standard construction is a dptree handler rooted in an Update filter, with an endpoint async function. Integration fragment:

```rust
let handler = Update::filter_message().endpoint(handle_message);
Dispatcher::builder(bot, handler)
    .enable_ctrlc_handler()
    .build()
    .dispatch()
    .await;
```

bot, Update/Dispatcher imports and handle_message must exist in the application. An endpoint commonly returns ResponseResult<()>; dependencies are supplied by type.

Enable macros for `#[derive(BotCommands, Clone)]`. Command variants can carry parsed arguments. Use filter_command/filter_mention_command when group mentions should be recognized. The derive parses commands; it does not authorize administration.

Place authorization filters before a sensitive endpoint. Keep a generic text handler after command-specific branches so it does not consume their updates. A branch whose filters neglect an update can fall through; an endpoint's error is not a request to try every other branch.

## 5. Dependency injection and dialogues

DispatcherBuilder.dependencies takes dptree::deps! values such as application configuration, a database handle or dialogue storage. Injection is type-based: mismatched or missing dependency types are a wiring error, not a reason to add globals.

Model multi-step state with an enum, Dialogue and a chosen storage implementation. InMemStorage loses state on process exit. Persist state when the user's workflow must survive restart and validate state schema changes during upgrades.

Dialogue storage is separate from orders, reminders, payments, inbox/outbox, and other business tables. Understand the storage key/scope used by teloxide; if the workflow needs independent per-user conversations in a group, design the application state accordingly.

## 6. Callbacks and messages

Filter callback queries with Update::filter_callback_query(). A CallbackQuery can have inline_message_id instead of an accessible message; its data is optional. Use the available variant rather than unwrapping fields.

Answer the callback using answer_callback_query with its typed query ID, then process a validated server-side action. Acknowledge rejected/expired taps too. Compare the user and target state/ownership before accepting callback payloads.

send_message is a Requester method and its request can be awaited. Optional fields are set through request setter traits, many re-exported by the prelude. IDs such as CallbackQueryId, FileId and message IDs are typed newtypes in recent versions; do not force arbitrary integers/strings into them without the documented constructor.

Keyboard markup uses teloxide::types; check which button variants/fields exist at the selected release. Escaping HTML/Markdown is separate from constructing markup. UI, Mini Apps and payments guides describe protocol concepts that must be mapped to actual crate support.

## 7. Media and downloads

Use InputFile::file, InputFile::url or InputFile::file_id as supported by the selected upload/send method. A local input file must remain available through the request. Reuse Telegram file IDs when suitable, and keep temporary files bounded.

For downloads, retrieve the Telegram File metadata and use teloxide's Download trait/helpers with the returned file path. Limit filesystem paths and output size and keep authorization for any application endpoint serving downloaded media.

Albums use a vector of the supported InputMedia variants. A file's Telegram size/account limits remain in force. Large-file requirements may justify the official local Bot API server; configure the base API URL through the documented Bot/client API rather than modifying request paths ad hoc.

## 8. Errors and request adaptors

Propagate RequestError from endpoints or map it to an application error. Distinguish a Telegram ApiError, RetryAfter, transport failure, invalid JSON, and I/O error.

Use the throttle feature/adaptor when request pacing is needed, but verify its supported methods and configured limits. A sample global rate does not cover every per-chat/API rule. Honor server retry delays and bound any custom retries.

Timeouts can leave a send's result unknown. For payments, orders and important broadcasts, use durable idempotency records/outbox handling rather than assuming retrying always produces one effect.

Configure Dispatcher error/default handlers to expose failures. Do not log the token, URLs containing it, or entire updates containing personal/payment data.

## 9. Webhooks and Axum listeners

With webhooks-axum, teloxide's webhooks::axum(bot, Options) helper sets a webhook, starts an Axum listener, and deletes the webhook when that listener is stopped. It is a live registration operation, not just a local server constructor.

For an existing server, inspect axum_to_router/axum_no_setup and own the registration lifecycle deliberately. Match the public HTTPS URL to proxy/router paths and validate the configured Telegram secret header.

Options control bind address/public URL and other supported fields. Add service-level body limits, request deadlines, durable receipt/deduplication, health checks and graceful shutdown. Do not keep polling active for the same token.

Read the versioned webhook example before composing listener startup with dispatch_with_listener or repl_with_listener. Listener errors and handler errors are different paths.

## 10. Async work and state

Avoid blocking Tokio's executor with synchronous database/network/process calls. Use async clients, or bounded spawn_blocking work for unavoidable blocking operations. A CPU-heavy job needs its own concurrency budget.

Never hold a std::sync lock guard across await. Use short critical sections or an appropriate async synchronization primitive, but do not turn a mutex into a global network queue.

Scope data by actual Telegram IDs. Do not assume a username is stable, every message has a user sender, or every update is a Message. Preserve sequence/idempotency requirements when configuring concurrent dispatch.

## 11. New API gaps and migration

First check a method and required parameters in the published docs. If unavailable, prefer a supported feature fallback or a deliberately isolated raw Bot API request using an existing HTTP client. Its validation, model/error handling and token redaction remain application responsibilities.

Upgrading to a Git revision/fork changes the tested surface and build dependencies. Explain that choice and pin the revision; do not market development-branch support as a released crate feature.

## 12. Verification

Run cargo fmt --check and cargo check with the selected features/toolchain. Use deserialized Update fixtures and fake request handling for dispatch and callback tests. Check malformed/expired state and restart behavior against the chosen local store.

A local build does not verify Telegram authentication, permissions, polling conflicts, webhook registration, transfer limits or payment fulfillment. State which integration checks actually ran.
