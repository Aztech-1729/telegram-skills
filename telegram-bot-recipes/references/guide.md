# Recipe setup and operating limits

Checked 2026-10-04. Contents: setup; moderation; reminders; quizzes; RSS; AI;
downloads; short links; validation and scaling.

## Setup

Copy the files from `assets/` into one project directory. Use Python 3.10+ and a
virtual environment. Install the base file and select one mode:

```sh
python -m pip install -r requirements.txt
python recipes.py --mode quiz
```

Configure `TELEGRAM_BOT_TOKEN`, `BOT_ALLOWED_USER_IDS` (comma-separated numeric IDs)
and optionally `RECIPE_DB` (defaults to `recipes.db`). The commands assume these
variables are already set securely by the shell, host or secret manager. Never
commit a real `.env` file. The SQLite path must persist across process restarts.
Connections are short-lived, explicitly closed and used in background threads.

Only one mode and one process consume updates in this starter. Update handling is
sequential; this is not a distributed scheduler. The access gate limits interactive
commands to configured users except in moderation mode, which observes group
messages and independently checks live administrators on each warning command.
Add product-specific `/start`, `/help` and quotas as required. Use
[bot UX](../../telegram-bot-ux/SKILL.md) for the ordinary command journey and
[accessibility](../../telegram-bot-accessibility/SKILL.md) for text/button/media
alternatives. Reminder list/cancel commands are included; other modes need their
own cancellation and recovery policy.

## Moderation

Run `--mode moderation`. Grant the bot the specific group rights needed and make
sure it receives the messages the product needs under Telegram privacy mode.
`/warn` must reply to an ordinary user's message. It checks the invoking user's
live membership, protects administrators, verifies the bot's restriction right,
then atomically increments a warning count scoped to group and user. At three
warnings it requests a ban. A failed ban leaves the warning history intact and
is logged without dumping credentials.

The anti-link handler exempts bots and live administrators and deletes only when
the bot has deletion rights. It is a basic text filter: entities, captions,
obfuscated links, exceptions, appeals and audit records need a product decision.
Anonymous sender-chat posts are not silently attributed to a human administrator.
Add `/mute`, expiry and unwarn with the same authorization checks if requested;
those commands are not present in this starter.

## Reminders

Run `--mode reminders`; `/remind 30m Call home` stores an integer Unix due time.
Positive minute/hour/day durations are bounded to a year. A JobQueue tick checks
up to 100 due rows every 30 seconds. The database, rather than a transient
`run_once` job, is the scheduling source.

The tick sends first and marks delivered after success. Each row has persisted
attempt count, next attempt time, terminal-failure flag and error category.
Confirmed rate limits honor `retry_after` and persist a conservative pause for the
reminder sender before processing more rows; network/timeouts back off; permission,
bad input and other failures become terminal for repair. Five failed attempts also
stop delivery. One failed item does not block later rows. Error bodies and message
contents are excluded from failure logs. The selected reminder policy accepts
possible duplicate delivery after an ambiguous send; a crash between send and
commit can also repeat a message. Multiple workers need leases and fencing; use
the advanced outbox implementation.

Retry and pause deadlines start from the actual failure time, not the due-row
selection time. This matters when earlier sends or the failed request are slow;
the whole server-requested wait follows the received failure. Deterministic
clock tests cover slow batches and fractional timestamps across a reopened store.

`/reminders` lists the user's first 20 pending/failed reminders in that chat with
UTC due times, and `/cancelreminder <id>` authorizes by both user and chat. Saved
forum/private bot topic IDs are used when sending; closed/deleted topics need a
repair policy rather than silently moving a reminder into a different topic.
Cancellation can race a row already selected by the delivery worker; it cannot
retract a dispatched send. For stronger cancellation semantics, use a durable
claim/cancel state machine as described in the advanced guide.
The starter upgrades old reminder tables without dropping rows; older rows lack
owner and topic metadata, so they still deliver but cannot be claimed or canceled
by an arbitrary user. Back up before adopting any schema change and define an
operator migration/removal process for those legacy rows.
Relative durations are independent of timezone. Calendar schedules require an
explicit timezone and daylight-saving policy and are not implemented here.

## Quiz

Run `--mode quiz`; `/quiz` creates an expiring random session ID. Button payloads
contain that ID, question step and answer index. The store verifies bounds, user,
chat, current step and expiry under `BEGIN IMMEDIATE` before scoring. Duplicate
deliveries or simultaneous presses cannot score the same step twice.

Scores are persistent and cumulative. The UI shows completion; it does not expose
a leaderboard command. A failed edit after a committed answer leaves the score
correct but can leave old buttons visible. Add a resumable quiz policy or render
the persisted step when adapting this for a larger product.

## RSS publisher

Run `--mode rss`. Install `feedparser` and `httpx`, then configure `RSS_FEEDS`
(comma-separated operator-selected HTTP(S) feeds) and `RSS_CHANNEL` (numeric ID
or channel username). Grant channel posting rights. The initial poll publishes
up to ten recent entries per feed; decide whether a new deployment should instead
seed the seen table without sending a backlog.

Fetches are asynchronous, time bounded, limited to two million decoded bytes and
do not follow redirects. Parsing runs in a thread. Only title and link are sent,
as plain text; feed HTML is not trusted as Telegram markup. Titles are bounded in
UTF-16 units; links too large for the message budget are skipped with a category
log, never silently truncated into another destination. Seen identities include
feed URL and a SHA-256 entry ID and are recorded after successful sends. This has
the same crash-after-send ambiguity as reminders. Feeds are configuration, not
arbitrary chat URLs. Add conditional requests and per-feed error isolation as needed.

## AI assistant

Run `--mode ai`. Install `openai`, configure `OPENAI_API_KEY` and `OPENAI_MODEL`
explicitly, and keep the allowed-user list small for the initial deployment.
The handler creates an `AsyncOpenAI` client with a timeout and bounded retries,
calls `responses.create` with `store=False`, reads `output_text` and sends plain
text in chunks bounded by UTF-16 units. It uses no tools or conversation history.
The local 4000-unit budget is conservative: `sendMessage` documents 4096
characters after entities parsing, while entity offsets/lengths explicitly use
UTF-16. The reminder text budget is 3000 UTF-16 units plus its prefix; do not
present these local choices as Telegram's exact character-counting algorithm.
`store=False` controls response storage, not every service-side retention policy.
Pick the model and cost limits for the actual account.

This is a one-shot completion with a typing indicator. For response-event streaming,
accumulate text deltas, handle errors/cancellation and use the rich messaging
skill's draft lifecycle. Keep secrets out of model input. If adding tools,
authorize external effects and validate arguments. Add budgets, an explicit group
mention/reply policy and a privacy explanation before offering a public assistant.

## Media downloader

Run `--mode download`. Install a current operator-reviewed `yt-dlp` package and
its runtime dependencies; configure `DOWNLOAD_HOSTS` with exact approved hostnames.
`/dl` accepts an absolute HTTP(S) URL without embedded credentials. It uses an
async argument-vector subprocess, disables external config and plugins, bounds
time/concurrency, avoids playlists, writes into a temporary directory, checks
the resulting file size and closes the upload stream. The expected exit101 from
`--max-downloads 1` still requires one complete, nonempty file within the upload
limit. Other nonzero exits are failures even if an output file exists. Timeout or cancellation kills
and awaits the process before cleaning the temporary directory.

The host check covers the initial URL. Extractors, redirects and media manifests
can contact other hosts. For untrusted users, run a worker with restricted network
egress, filesystem/process isolation, disk/CPU quotas and reviewed extractors.
The downloader's size option is advisory for unknown-size streams; the final
upload check does not enforce a disk quota. It sends a document rather than guessing
media type. Upload limits depend on transport and method; a local Bot API server
is a separate deployment choice, not a permission or reliability bypass.

## Short links

Run `--mode shortener`. Configure `SHORT_BASE_URL` as the public redirect service
base URL. `/shorten` validates and stores an absolute HTTP(S) destination and
returns a random eight-character code. The bot does not fetch the destination.
Install `fastapi` and `uvicorn`; start the companion in the same project directory:

```sh
uvicorn redirect_service:app --host 127.0.0.1 --port 8000
```

Put it behind the domain's TLS reverse proxy. Both processes must use the same
absolute `RECIPE_DB` path on one persistent host. Existing valid codes return 302;
others return 404. Public deployments need destination abuse controls,
reporting/removal, expiry and rate limits. HTTP URL validation does not establish trust.

## Checks and next steps

Copy `tests/` as well, then run `python -m unittest discover -s tests`. Tests use
temporary databases and no Telegram/OpenAI/download calls. They verify failed-send
retryability and row isolation, bounded retry state, persistence/schema migration,
reminder ownership/topic routing, quiz ownership/expiry/replay, concurrent scoring,
warning scope/anonymous actors, callback recovery, text bounds and URL schemes.
Import/API checks are separate from live behavior.
Add synthetic handler tests for new commands, then test with a development bot.
