# Telegram.Bot diagnostics

Focused source review: **2026-10-04**, package 22.10.3.2. Use the actual NuGet lock/restore result and a small deserialized Update fixture; inspect the tagged client rather than translating an older tutorial.

| Symptom | Check and repair |
| --- | --- |
| SendMessageAsync or polling imports no longer compile | Current convenience calls use names such as `SendMessage`. Match the package's namespaces, method parameters and hosting model; avoid mixing generations. |
| Callback or payment code never runs | `OnMessage` consumes message-like updates when subscribed. Route other kinds through `OnUpdate`; successful payment is inside a message, while pre-checkout is a separate update. Starting a second receiver will not fix routing. |
| An edit repeats a business action | The message event includes edits, channel posts and business messages. Filter UpdateType explicitly or route variants through the application's one dispatcher. The starter accepts only `UpdateType.Message`. |
| A forum reply leaves its topic | SendMessageRequest needs MessageThreadId for a source topic. The starter's pure request builder preserves it and leaves it unset for ordinary messages. Business connections/direct-message topics require their own fields when that mode is supported. |
| DbContext throws concurrent-operation errors | A singleton client can be shared; an EF DbContext/unit of work cannot be used by concurrent operations. Create a service scope per operation and use transactions/concurrency tokens for shared business rows. |
| A 429 takes longer than expected or retries multiply | The tagged client retries only within RetryThreshold/RetryCount conditions. Account for that client policy before adding an outer retry. Network timeouts can have unknown delivery results; blind send retries can duplicate output. |
| Console shutdown works but hosting shutdown loses tasks | Event reception starts in the background when subscribed. Cancellation stops requests, but waiting on an unrelated delay does not prove every handler drained. For a hosted worker, use the receiver API with an awaited lifecycle and a stop deadline. |

## Diagnose ingress separately

An ASP.NET endpoint must deserialize with the library's Telegram JSON converters, reject missing/wrong secret headers, and distinguish queue acceptance from side-effect completion. Check proxy path/TLS and request limits before debugging handler filters. Preserve update IDs in a durable inbox when replays matter.

## Offline request routing

`dotnet run -- --self-test` exits before token lookup/client creation. It checks plain text, a large negative chat ID, forum routing, ignored edits/business updates and non-text messages. Build with the selected SDK before relying on those tests. Live rendering, authentication, delivery and host lifecycle remain separate validation.
