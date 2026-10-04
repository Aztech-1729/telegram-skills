# teloxide build and dispatch diagnostics

Focused source review: **2026-10-04**, published teloxide 0.17.0. The crate baseline and current Telegram server API are separate surfaces.

| Symptom | Check and repair |
| --- | --- |
| A module/derive is missing | Run `cargo tree -e features`; commands, webhook listeners and storage backends need the matching crate feature. Check published 0.17.0 feature names, then `cargo check` the actual target. |
| Cargo says the Rust version is too old | The crate declares an MSRV; resolved transitive dependencies can require more. Inspect the locked graph and supported toolchain, rather than claiming the starter's rust-version guarantees every fresh resolution. |
| Handler dependency injection panics | dptree injects by type. Check endpoint argument types against `dependencies(dptree::deps![...])`; a different wrapper/storage type is not interchangeable. |
| User flows in a group overwrite each other | Built-in Dialogue storage is keyed by chat. Design separate per-user/topic state when required, and choose a matching dispatch distribution key. Default dispatch serializes updates sharing a chat; updates with no distribution key run concurrently. |
| Polling appears frozen during CPU/DB work | Avoid blocking the Tokio executor or holding a synchronous lock across await. A spawn_blocking task still needs bounds and ownership; canceling its await does not reliably stop already-started blocking work. |
| Reply appears outside a forum topic | The starter copies Message.thread_id only for a topic message to SendMessage.message_thread_id. Other modes require their own supported routing fields; do not flatten all destination types to ChatId. |
| A new Telegram feature does not compile | Confirm the published Requester/payload docs. Development support is not released-crate support. Upgrade/pin an explicit revision or implement a small tested wire adapter rather than inventing a setter. |

## Listener lifecycle

`webhooks::axum` registers a live webhook and manages deletion on stop. For an existing Axum server choose the appropriate router/no-setup integration and own registration deliberately. Options supports an explicit secret; leaving it unset lets teloxide generate one. Stable multi-instance ingress needs a shared configured secret and a durable receipt policy.

Do not assume a handler error recreates a consumed update. Track accepted updates/business effects and distinguish listener failures from endpoint failures. Configure error/default handlers to surface unrouted variants without dumping private updates or token-bearing URLs.

## Request tests before reception

`cargo test` builds the starter and tests serialized request payloads and ignored non-text input using a synthetic token; request construction is lazy and no request is awaited. Run `cargo fmt --check` and `cargo check` for the chosen feature set. Live listeners, rights, media transfers and persistence are separate checks.
