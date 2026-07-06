# hermes-discord-status-line

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that sends a customizable status line as a follow-up Discord message after each response.

Shows API timing, context window usage, token counts, and model name — inspired by [Claude Code's status line](https://code.claude.com/docs/en/statusline).

Inspired by the status line format used in [Kimaki](https://github.com/remorses/kimaki).

## What it looks like (approximately)

> *4.5s ⋅ 7% ⋅ ( 71K/1M ) ⋅ deepseek-v4-flash*

Rendered as an italic line below the bot's response. (Use `-# *...*` in your template if you want Discord subtext instead.)

## Installation

Symlink (or copy) into your Hermes plugins directory:

```bash
ln -s ~/hermes-discord-status-line ~/.hermes/plugins/discord-status-line
```

Hermes auto-discovers plugins on startup. No other configuration needed.

## Configuration

Edit `config.yaml` in the plugin directory to customize the format:

```yaml
# Available variables (see full reference below):
#   {duration}   - API time for the turn
#   {model}      - model name

template: "-# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}*"
```

### Variable reference

| Variable           | Description                          | Example            |
| ------------------ | ------------------------------------ | ------------------ |
| `{duration}`       | API time for the turn                | `4.5s`, `1m 23s`  |
| `{ctx_pct}`        | Context window usage                 | `7%`, `?%`        |
| `{tokens}`         | Used/total tokens                    | `( 71K/1M )`       |
| `{model}`          | Model name                           | `deepseek-v4-flash` |
| `{call_count}`     | API calls this turn                  | `3`               |
| `{input_tokens}`   | Prompt/input tokens                  | `71K`             |
| `{output_tokens}`  | Completion/output tokens             | `2.3K`            |
| `{total_tokens}`   | Total tokens this turn               | `73K`             |
| `{cache_pct}`      | Cache hit percentage                 | `82%`, empty if N/A |
| `{finish_reason}`  | Why the model stopped                | `stop`, `length`, `tool_use` |
| `{msg_count}`      | Messages sent in the API request     | `12`              |
| `{tool_calls}`     | Tool calls in the response           | `3`, `0`          |
| `{chars}`          | Characters in the assistant response | `1.2K`            |
| `{provider}`       | API provider                         | `openrouter`      |
| `{session_id}`     | Hermes session ID for the turn       | `20260706_abc123` |

### Examples

Minimal:
```yaml
template: "-# *{model} ⋅ {duration}*"
```

With call count:
```yaml
template: "-# *{model} ⋅ {duration} ⋅ {ctx_pct} ⋅ {call_count} calls*"
```

Tokens only:
```yaml
template: "-# *{tokens} ⋅ {model}*"
```

With session ID:
```yaml
template: "-# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}* `{session_id}`"
```

Session labeled:
```yaml
template: "-# *{duration} ⋅ {model}* `session:{session_id}`"
```

## How it works

1. Hooks into `post_api_request` to accumulate per-turn API stats (duration, token usage, model, call count)
2. Monkey-patches `DiscordAdapter.send` to append a follow-up message with the rendered template
3. Reads `config.yaml` on first use (cached for the session)

> **Warning:** This plugin currently uses monkey-patching because Hermes doesn't yet expose a hook for post-response actions. If Hermes renames or restructures its internal adapter, the plugin will break silently (the status line simply won't appear). Use at your own risk. See [Compatibility status](#compatibility-status) below.

## Compatibility status

**Works today** with any Hermes instance that has Discord platform support. Symlink it in and restart.

**Current limitations** (until upstream changes land):

- The plugin monkey-patches `DiscordAdapter.send` because Hermes doesn't yet provide a hook for post-response actions. This is fragile — if Hermes renames or restructures the adapter, the plugin breaks silently (the status line just won't appear).
- Context window percentage requires `agent.models_dev.get_model_capabilities` to be available. If it's missing, the plugin falls back to `?%` and omits the token count.
- Only API-level data is available (duration, tokens, model). Session-level info like active personality, plugin state (e.g. whether a /converse mode is on) is not accessible to plugins yet. Session ID (`{session_id}`) was added via hook kwargs and is now available as a template variable.

**Upstream PR** that would fix this:

**[#42416 -- feat(plugins): propagate session context to plugin hooks](https://github.com/NousResearch/hermes-agent/pull/42416)**

Once merged:
- The monkey-patch can be replaced with a proper hook-based approach
- New template variables become available: `{personality}`, plugin states, and anything else Hermes exposes through session context
- The plugin becomes a clean citizen with no internal API dependencies

> **Note:** `{session_id}` was added ahead of this PR — it's already available via the existing `post_api_request` hook kwargs, captured and exposed as a template variable without needing the upstream change.

## Enabling / Disabling

- **Enable**: plugin exists in `~/.hermes/plugins/` (loaded on Hermes startup)
- **Disable**: remove the symlink or directory

## Requirements

- Hermes Agent with Discord platform support
- PyYAML (`pip install pyyaml`)
