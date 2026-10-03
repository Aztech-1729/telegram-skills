# Install Telegram Skills

The canonical source is
[Aztech-1729/telegram-skills](https://github.com/Aztech-1729/telegram-skills).
Install the complete 18-skill pack to preserve its framework/feature links and
supporting resources. Installation makes instructions available to your agent;
running a starter later requires its own language dependencies and bot
configuration.

## One command for supported agents

From your application project's directory:

```sh
npx --yes skills add Aztech-1729/telegram-skills --all
```

`--all` selects all skills, targets every agent supported by the CLI and skips
installer confirmation prompts. Unconfigured agent-specific project directories
may be skipped; inspect the output and rerun after configuring that host.
The [supported-agent list](https://github.com/vercel-labs/skills#supported-agents)
defines the actual coverage. A host needs a compatible skill filesystem; a chat
interface without access to this project cannot discover a local installation.

To install the complete pack only for Codex, Claude Code and OpenCode:

```sh
npx --yes skills add Aztech-1729/telegram-skills --skill '*' --agent codex claude-code opencode --yes
```

Replace the agent list with the CLI IDs you use, such as `cursor` or
`github-copilot`. Keep `'*'` quoted so your shell passes the wildcard to the
installer. For a repeatable CLI version, replace `skills` with `skills@1.7.0`.
The [CLI option definitions](https://github.com/vercel-labs/skills/blob/main/src/cli.ts)
document those flags.

Prerequisites are Git, npm and Node.js **22.20.0 or newer**, as declared by
[skills 1.7.0](https://registry.npmjs.org/skills/1.7.0). The public download needs
network access but no personal access token, Telegram token or AI API key. If
PowerShell blocks the `npx.ps1` launcher, use `npx.cmd` with the same arguments.

## Project or global installation

The default installation belongs to the current project. It keeps the pack
available to agents working in that project and leaves other projects separate.
The CLI normally keeps a canonical skill copy and links agent directories to it.
Add `--copy` when you need independent copies instead of links.

For a user-wide installation to the three selected agents:

```sh
npx --yes skills add Aztech-1729/telegram-skills --skill '*' --agent codex claude-code opencode --global --yes
```

These are the selected CLI 1.7.0 destination directories; append a skill name,
such as `telegram-bot-aiogram`, to find its complete folder:

| Agent | Project destination | CLI global destination |
|---|---|---|
| Codex | `.agents/skills/` | `~/.codex/skills/`, or the configured `CODEX_HOME/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/`, or the configured `CLAUDE_CONFIG_DIR/skills/` |
| OpenCode | `.agents/skills/` | `~/.config/opencode/skills/`, honoring the XDG configuration directory |

The [CLI's agent definitions](https://github.com/vercel-labs/skills/blob/main/src/agents.ts)
are the source for these destinations. Current Codex documentation also lists
`~/.agents/skills/` for native user skills; its project path is `.agents/skills/`.
Use the project install as the shared default, or the native plugin route below
for Codex distribution. For a manual user install, use the location documented
by your installed host. Custom configuration roots can change a global location.
[Codex discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills),
[Claude Code discovery](https://code.claude.com/docs/en/skills#choose-where-skills-load)
and [OpenCode discovery](https://opencode.ai/docs/skills/#place-files) describe
the native rules.

All 18 skill folders include their references, scripts and assets where supplied.
The skill installer does not copy every repository file: shared research,
validation and automation records remain available in
[the repository docs](https://github.com/Aztech-1729/telegram-skills/tree/main/docs).
The installed pack does not activate this repository's maintainer heartbeat on
your computer.

## Native Codex and Claude Code plugins

The repository also defines an **aztech** marketplace containing the **telegram**
plugin. These are package identifiers; the GitHub source remains
`Aztech-1729/telegram-skills`. Choose this route when you want the host's native
plugin management rather than individual installed skill folders.

For Codex CLI:

```sh
codex plugin marketplace add Aztech-1729/telegram-skills
codex plugin add telegram@aztech
```

For Claude Code CLI:

```sh
claude plugin marketplace add Aztech-1729/telegram-skills
claude plugin install telegram@aztech
```

The command names differ between hosts. Registering this repository as a local
marketplace does not publish it in a host's curated public directory. The native
manifests bundle the existing root skill directories; there is no separate
`aztech/telegram` GitHub repository. Prefer one installation route per host to
avoid duplicate skill entries. Native plugin scope and updates follow the
host's plugin manager rather than `skills update`.

The native packaging was checked with Codex **0.160.0** and Claude Code
**2.1.282**, using isolated configurations. All 18 skills and their assets were
retained. See the official
[Codex plugin guide](https://developers.openai.com/plugins/build/plugins) and
[Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference)
for host-specific management options.

## Verify and use the pack

List this project's installed skills:

```sh
npx --yes skills list --agent codex claude-code opencode
```

For a global install, add `--global`. The complete pack has 18 names beginning
with `telegram-bot-`. Check that the selected host can see the same skills in its
selector or skill tool. Start a new session or restart the host if its discovery
view is stale.

| Host | Explicit use after skill-folder installation |
|---|---|
| Codex | Include `$telegram-bot-aiogram` in your request, or select it from the skill picker |
| Claude Code | Invoke `/telegram-bot-aiogram` or ask for the skill by name |
| OpenCode | Ask it to load `telegram-bot-aiogram`; its native `skill` tool loads the selected instructions |

Plugin-installed skills can use a host's namespaced selector, such as
`$telegram:telegram-bot-aiogram` in Codex or `/telegram:telegram-bot-aiogram`
in Claude Code. Native hosts can also select skills from the request and their
activation descriptions. Read the
[task catalog](../README.md#start-here), select the existing framework, then add
the needed feature skills. Installing all 18 does not require loading all their
bodies and references into every conversation.

Give a terminal-capable agent this instruction when you want it to install and
use the pack:

```text
Install all 18 skills from Aztech-1729/telegram-skills into this project for
my agent, preserving every skill's supporting resources. Use the skills CLI
with --skill '*' and my agent's ID; report any missing installation prerequisite.
Verify the installed names. For my Telegram task, identify the existing framework,
load its skill and the relevant feature skills, and read only the references
needed for the requested behavior. Preserve the project's existing stack.
```

An agent that cannot install local packages can still read the repository and
the linked skill files directly when its host allows that access.

## Check installation from a source checkout

The contributor check uses the locked real CLI in temporary projects:

```sh
npm ci --ignore-scripts
python scripts/validate_pack.py
python scripts/check_installation.py
```

Pack validation includes the native plugin manifests, marketplace identities,
versions and all 18 skill paths. The installation check verifies every supplied
skill resource, allowing Git text line-ending normalization, and resolves local
Markdown routes in both
all-supported-agent mode and independent copies for Codex, Claude Code and
OpenCode. It leaves your actual agent configuration and installed user skills
alone. The hosted workflow repeats installation checks across its configured
operating systems. These checks establish packaging/discovery, not the behavior
of a deployed Telegram application.

## Update or remove installed skills

To refresh only this pack from its current source, repeat your original `skills
add` command with the same scope and agent list. Do not make local customizations
inside the installed pack that you expect a reinstall to preserve; keep project
adaptations in your application.

The CLI also offers explicit scope updates:

```sh
npx --yes skills update --project --yes
npx --yes skills update --global --yes
```

Each command updates all installed skills in that scope, including other packs.
Its [update documentation](https://github.com/vercel-labs/skills#skills-update)
also describes selecting individual names.

Remove one installed skill from the selected project agents:

```sh
npx --yes skills remove telegram-bot-aiogram --agent codex claude-code opencode --yes
```

Add `--global` to remove it from a global installation. To remove the complete
pack while preserving other packs, use the interactive command and select only
the 18 `telegram-bot-` entries:

```sh
npx --yes skills remove --agent codex claude-code opencode
```

The [remove command](https://github.com/vercel-labs/skills#skills-remove) accepts
multiple explicit names. `skills remove --all` removes every skill in its scope;
it is not a Telegram-pack-only removal command. Avoid editing the CLI's managed
canonical copies or links by hand.
