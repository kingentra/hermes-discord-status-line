# hermes-discord-status-line

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that sends a customizable status line as a follow-up Discord message after each response.

Shows API timing, context window usage, token counts, and model name — inspired by Claude Code's status line.

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

## Enabling / Disabling

- **Enable**: plugin exists in `~/.hermes/plugins/` (loaded on Hermes startup)
- **Disable**: remove the symlink or directory

## Requirements

- Hermes Agent with Discord platform support
- PyYAML (`pip install pyyaml`)
