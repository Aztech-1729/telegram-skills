# Sources and validation

**Research cutoff and review date: 2026-10-03.**

## Release boundary

- Published **teloxide 0.17.0**, released **2025-07-11**, is the starter pin. Its published crate metadata declares **Rust 1.82**.
- The published changelog lists **Bot API 9.1** support in 0.17.0.
- The checked master snapshot, commit **3c46b96e0dc0cabc75d6430c4566d7e2e12fd233** dated **2026-08-08**, lists **9.2 under unreleased**, and its workspace/README asks for **Rust 1.85**.
- Telegram's **Bot API 10.3** release is a separate protocol reference. Do not infer 10.3 SDK support from current Telegram documentation.

The starter's package MSRV describes its selected released crate baseline. Transitive dependency resolution may require a newer toolchain; cargo check/Cargo.lock are needed to establish an application's actual build.

## Primary sources

- [Published teloxide 0.17.0 API](https://docs.rs/teloxide/0.17.0/teloxide/): public modules and traits.
- [Published crate metadata](https://crates.io/api/v1/crates/teloxide/0.17.0): release timestamp and declared rust_version.
- [Project changelog](https://github.com/teloxide/teloxide/blob/3c46b96e0dc0cabc75d6430c4566d7e2e12fd233/CHANGELOG.md): released 0.17.0 features versus unreleased development changes.
- [Project workspace](https://github.com/teloxide/teloxide/blob/3c46b96e0dc0cabc75d6430c4566d7e2e12fd233/Cargo.toml): development toolchain baseline.
- [repl](https://docs.rs/teloxide/0.17.0/teloxide/repls/fn.repl.html): async message endpoint, dependency contract and single-receiver warning.
- [Dispatching](https://docs.rs/teloxide/0.17.0/teloxide/dispatching/index.html): dptree filters/branches, endpoint dependencies, Dispatcher versus REPL.
- [Dialogue storage](https://docs.rs/teloxide/0.17.0/teloxide/dispatching/dialogue/index.html): InMem and persistent storage boundaries.
- [Command parsing](https://docs.rs/teloxide/0.17.0/teloxide/utils/command/index.html): BotCommands and command filters.
- [Axum webhook listener](https://docs.rs/teloxide/0.17.0/teloxide/update_listeners/webhooks/fn.axum.html): registration/server/delete lifecycle and feature gates.
- [RequestError](https://docs.rs/teloxide/0.17.0/teloxide/enum.RequestError.html): API, delay, network/JSON/I/O errors.
- [Requester](https://docs.rs/teloxide/0.17.0/teloxide/requests/trait.Requester.html) and [types](https://docs.rs/teloxide/0.17.0/teloxide/types/index.html): actual typed request surface/newtypes.
- [Telegram Bot API](https://core.telegram.org/bots/api): authoritative server fields, permissions, callbacks, delivery and modern API features.
- [Tokio blocking work](https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html): async-runtime boundary for blocking code.

## Validation

No cargo/rustc toolchain was installed in the available environment. The original Cargo.toml/main.rs asset and guide fragments were reviewed against the published documentation and primary source, but **cargo check and cargo fmt were not run**.

No Rust program was started; no Telegram request or webhook operation was made. The guide directs the implementing agent to compile the chosen feature set before relying on these examples.
