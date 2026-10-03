# Automated maintenance

This repository runs validation, observes official sources and proposes dependency
updates through GitHub Actions and Dependabot. Automation can refresh evidence and
merge eligible changes after required validation. Changes to the meaning of a
guide, API recommendation or example still require content review and testing.

The skill source registers retain their **2026-10-03 editorial review date** until
the relevant content is actually reviewed again. A later successful fetch is a
separate observation, not a new review date.

## Active workflows

| Workflow | Trigger | Result |
|---|---|---|
| [Validate skill pack](../.github/workflows/validate.yml) | Push, pull request, manual run and Monday 04:17 UTC | Pack and behavior checks, language builds, public HTTP checks, optional default-branch `getMe` and the required `validation` gate |
| [Refresh upstream evidence](../.github/workflows/upstream-refresh.yml) | Daily 04:37 UTC and manual run on the default branch | Observed source state, aggregate/per-skill reports, a generated-evidence PR, native pull-request validation approval and a deduplicated source-review issue when needed |
| [Eligible dependency auto-merge](../.github/workflows/dependabot-automerge.yml) | Eligible Dependabot pull-request events | Enables protected auto-merge for verified minor/patch updates within allowed paths |
| [Automation alerts](../.github/workflows/automation-alerts.yml) | Completion of validation/refresh runs | Records default-branch failures/recovery; keeps eligible bot PRs current with main and starts native tests |
| [Dependabot](../.github/dependabot.yml) | Weekly | Dependency PRs for pip, npm, Go modules, Maven, NuGet, Composer, Cargo and GitHub Actions |

Times are UTC. The [Actions history](https://github.com/Aztech-1729/telegram-skills/actions)
records actual execution. The [validation record](VALIDATION.md) links a successful
13-job hosted run and explains what each check establishes.

## What the source refresh observes

[The monitor](../scripts/check_upstream.py) harvests HTTPS links from every
`telegram-bot-*/references/sources.md`, deduplicates URL fragments and adds the
documentation and release feeds in [the source configuration](../automation/sources.json).
The generated [upstream status](UPSTREAM_STATUS.md) reports the current source
count, attempts, unavailable sources, pending changes and observed versions. Each
skill also has a generated `references/upstream-status.md` for its own sources.

HTML is normalized to useful page content, and structured release feeds retain
relevant release fields. The monitor hashes that normalized content with SHA-256;
it records successful observation dates and available release versions in
[`automation/upstream-state.json`](../automation/upstream-state.json). Stable
releases are the default; any intentional prerelease channel is explicit in the
source configuration. These versions are observations, not silently upgraded
dependencies or a claim that a starter supports them.

The configuration restricts allowed HTTPS origins and paths, including redirect
destinations. GitHub file views use official raw content where configured.
Explicit official source mappings provide alternatives for selected unavailable
documentation hosts. Request size, duration, retries and concurrency are bounded.
An unavailable source retains its last successful hash and date and is reported
as unavailable. It never becomes accepted content.

The first fetch establishes an observed baseline. A later changed hash adds a
persistent pending-review marker. Unchanged later fetches do not clear it. Layout
or release-note formatting changes can also alter a hash, so a changed source is
a reason to inspect it, not proof that the guide is wrong. Conversely, an unchanged
hash does not prove the guide is correct.

## Trust boundary and generated PRs

Fetched pages and release metadata are untrusted input. The monitor does not
execute them, send them to a model or turn their text into skill instructions.
The automated publication allowlist contains only:

- `automation/upstream-state.json`;
- `docs/UPSTREAM_STATUS.md`;
- `telegram-bot-*/references/upstream-status.md`.

`SKILL.md`, guides, source registers, dependency manifests, scripts, workflows and
the source allowlist require their own reviewed changes. The daily generated PR
therefore updates observation evidence; pending semantic changes stay visible for
a maintainer to address. Changing `automation/sources.json` changes the trust
boundary and needs review of the destination and its ownership.

The refresh checks out trusted default-branch code without persisted checkout
credentials. Its publishing step uses the run's short-lived `GITHUB_TOKEN` to
update the automation branch and PR, start validation and request protected
auto-merge. No personal access token is stored for this automation.

GitHub creates approval-required pull-request runs for token-created PRs. The
refresh approves only the native validation run for its own generated PR and exact
commit, after verifying the repository, author, branch and workflow identity.
Native pull-request checks satisfy the required merge gate; manually dispatched
workflow checks do not qualify as required pull-request checks.
[GitHub documents the token-trigger rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow).

The default branch requires the `validation` check with an up-to-date branch.
After successful validation, the maintenance job updates already eligible bot PRs
that have fallen behind main and approves their exact native test runs.
Auto-merge waits for the required gate; it does not bypass it. The automation
verifies that the gate is configured before requesting auto-merge. Branch deletion
and force pushes are disabled on the protected default branch; an administrator's
emergency bypass is outside the automated merge path.

## Dependency updates

Dependabot checks eight ecosystems weekly. Minor and patch changes are eligible
for auto-merge only after verified Dependabot metadata, author/repository checks,
allowed-file checks and required validation. Major upgrades remain manual. A
minor/patch label alone is not proof of compatibility; the applicable tests and
builds still have to succeed.

Dependency PRs may update only the configured manifests and lock files. For
GitHub Actions, the eligible diff is restricted to immutable action references;
changes to scripts, workflow permissions or job behavior do not qualify. The
privileged `pull_request_target` auto-merge workflow never checks out or executes
pull-request code. Updating a dependency does not automatically update a guide's
reviewed version table or certify new API behavior.

## Permissions and secrets

| Workflow | Token permissions | Boundary |
|---|---|---|
| Validation | `contents: read` | Pull-request checks have no Telegram secret; credentials are not persisted by checkout |
| Source refresh | Job-level `contents`, `pull-requests`, `actions` and `issues`: write; no default permissions | Trusted default-branch checkout; publishing token is passed only to the publishing step |
| Dependabot auto-merge | Job-level `contents` and `pull-requests`: write; no default permissions | Verifies metadata and allowed diffs without checking out PR code |
| Update maintenance | Job-level `contents`, `pull-requests` and `actions`: write | Trusted main; only already eligible, auto-merge-enabled bot PRs are updated |
| Failure alerts | `contents: read`, `issues: write`, `actions: read` | Uses trusted default-branch code and workflow metadata, not PR artifacts or code |

Repository settings must permit Actions to create pull requests and use the
declared token permissions. Auto-merge and the required `validation` branch check
must remain enabled. Organization or repository policy changes can block a run;
the workflow logs and failure issue identify that condition.

`TELEGRAM_TEST_BOT_TOKEN` is the only optional Telegram credential. Keep it in
GitHub Actions repository secrets and use a dedicated test bot. It is provided
only to the read-only authentication step on the default branch, never to
pull-request runs or dispatches on another branch. That step calls only `getMe`;
it does not send messages, make payments, read chat history or change webhooks.
Without the secret the step explicitly skips. A revoked, expired or invalid
credential requires maintenance.

## Review and clear a pending source change

1. Open the source-review issue and the affected entries in
   [upstream status](UPSTREAM_STATUS.md). Inspect the official source change and
   the affected skill's guide, source register, version pins and examples.
2. Update the guide or example where necessary. If the source change is cosmetic
   or irrelevant, record that finding in the review PR. Run relevant offline
   checks and builds; test live behavior when the change requires it. Record
   actual scope and results.
3. Refresh the observations so the review refers to the current hash. In
   `automation/upstream-state.json`, for each fully reviewed source, set
   `reviewed_sha256` to its current `sha256`, set `editorial_reviewed_at` to the
   review's ISO 8601 timestamp, and remove `pending_change_since`. Do not clear
   unrelated entries or replace a failed fetch with an assumed success.
4. Update a skill's dated source register only when its relevant content was
   actually reviewed. Regenerate the reports, inspect the diff and submit the
   content/state changes together for review and validation. If the source
   changes again during regeneration, its pending marker returns and needs
   another review.

From the repository root:

```sh
python scripts/check_upstream.py --write --report-json upstream-report.json
python scripts/render_skill_status.py
python scripts/validate_pack.py
python scripts/run_offline_checks.py
python -m unittest discover -s tests -p 'test_*.py'
```

The report JSON is an operational output, not an instructional source. Without
`--write`, the monitor reports observations without replacing tracked state or
Markdown. `--strict` makes any unavailable source fail the command. The normal
refresh records upstream outages without failing solely for them, so the report
and source-review issue can still be published; script or publication failures
are handled by the workflow failure alert.

## Operation and limits

Source changes and unavailable sources share a deduplicated review issue, and
repeated workflow failures update the existing failure issue instead of opening
one on every run. Recovery is recorded when the corresponding condition clears.
Use the issue and linked run logs to distinguish an upstream outage, dependency
regression, changed repository policy and a failed maintenance script.

GitHub schedules are best effort: runs may be delayed or dropped under load, and
scheduled workflows in public repositories are disabled after 60 days without
repository activity. Re-enable a disabled workflow in Actions and run it manually
to establish a fresh result. These are
[GitHub's documented schedule limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Secrets can stop working, upstream services can disappear and package releases
can need human decisions. A workflow cannot alert about its own absence if it
never runs. Check the latest run and observation timestamps when freshness
matters. This system provides recurring evidence and bounded updates; it does not
promise perpetual maintenance or comprehensive end-to-end Telegram coverage.
