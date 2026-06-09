# hermes-discord-status-line

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that sends a customizable status line as a follow-up Discord message after each response.

Shows API timing, context window usage, token counts, and model name — inspired by [Claude Code's status line](https://code.claude.com/docs/en/statusline).

Inspired by the status line format used in [Kimaki](https://github.com/remorses/kimaki).

## What it looks like

```
-# *4.5s ⋅ 7% ⋅ ( 71K/1M ) ⋅ deepseek-v4-flash*
```

Rendered as a subtle subtext line below the bot's response.

## Installation

Symlink (or copy) into your Hermes plugins directory:

```bash
ln -s ~/hermes-discord-status-line ~/.hermes/plugins/discord-status-line
```

Hermes auto-discovers plugins on startup. No other configuration needed.

## Configuration

Edit `config.yaml` in the plugin directory to customize the format:

```yaml
# Available variables:
#   {duration}   - API time for the turn (e.g. "4.5s", "1m 23s")
#   {ctx_pct}    - context window usage percentage (e.g. "7%", "?%")
#   {tokens}     - used/total tokens (e.g. "( 71K/1M )", empty if unknown)
#   {model}      - model name (e.g. "deepseek-v4-flash")
#   {call_count} - number of API calls this turn (e.g. "3")

template: "-# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}*"
```

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

## How it works

1. Hooks into `post_api_request` to accumulate per-turn API stats (duration, token usage, model, call count)
2. Monkey-patches `DiscordAdapter.send` to append a follow-up message with the rendered template
3. Reads `config.yaml` on first use (cached for the session)

## Compatibility status

**Works today** with any Hermes instance that has Discord platform support. Symlink it in and restart.

**Current limitations** (until upstream changes land):

- The plugin monkey-patches `DiscordAdapter.send` because Hermes doesn't yet provide a hook for post-response actions. This is fragile — if Hermes renames or restructures the adapter, the plugin breaks silently (the status line just won't appear).
- Context window percentage requires `agent.models_dev.get_model_capabilities` to be available. If it's missing, the plugin falls back to `?%` and omits the token count.
- Only API-level data is available (duration, tokens, model). Session-level info like active personality, plugin state (e.g. whether a /converse mode is on), or session ID is not accessible to plugins yet.

**Upstream PR** that would fix this:

**[#42416 -- feat(plugins): propagate session context to plugin hooks](https://github.com/NousResearch/hermes-agent/pull/42416)**

Once merged:
- The monkey-patch can be replaced with a proper hook-based approach
- New template variables become available: `{personality}`, `{session_id}`, plugin states, and anything else Hermes exposes through session context
- The plugin becomes a clean citizen with no internal API dependencies

## Enabling / Disabling

- **Enable**: plugin exists in `~/.hermes/plugins/` (loaded on Hermes startup)
- **Disable**: remove the symlink or directory

## Requirements

- Hermes Agent with Discord platform support
- PyYAML (`pip install pyyaml`)
