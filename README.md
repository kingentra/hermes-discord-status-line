# Hermes Discord status line plugin

A lightweight Hermes Discord plugin that appends a configurable status line after each response.

It can show response timing, context usage, token counts, model, provider, and tool-call information at a glance.

## What it can show

- Response duration
- Context usage percentage
- Token counts
- Model name
- Provider name
- Tool-call count
- Optional debug session ID

## Installation

Copy or symlink this repository into your Hermes plugins directory:

```bash
ln -s ~/hermes-discord-status-line ~/.hermes/plugins/discord-status-line
```

Hermes auto-discovers plugins on startup. No additional registry step is required.

## Configuration

Edit `config.yaml` in the plugin directory.

```yaml
template: "-# *{duration} • ctx {ctx_pct} • {tokens} • tools:{tool_calls} • {model}*"
```

You can customize the template to add or remove fields as needed.

## Available variables

| Variable | Description | Example |
| --- | --- | --- |
| `{duration}` | Turn duration or elapsed time | `4.5s` |
| `{ctx_pct}` | Context usage percentage | `7%` |
| `{tokens}` | Used or total token summary | `( 71K/1M )` |
| `{model}` | Model name | `deepseek-v4-flash` |
| `{tool_calls}` | Tool calls in the response | `3` |
| `{call_count}` | API calls in the turn | `3` |
| `{input_tokens}` | Prompt or input tokens | `71K` |
| `{output_tokens}` | Completion or output tokens | `2.3K` |
| `{total_tokens}` | Total tokens for the turn | `73K` |
| `{cache_pct}` | Cache hit percentage | `82%` |
| `{finish_reason}` | Why the model stopped | `stop` |
| `{msg_count}` | Messages sent in the API request | `12` |
| `{chars}` | Characters in the assistant response | `1.2K` |
| `{provider}` | API provider | `openrouter` |
| `{session_id}` | Hermes session ID for the turn | `20260706_abc123` |

**Warning:** `{session_id}` is debug/private information. Do not show it by default in public channels.

## Examples

Minimal:

```yaml
template: "-# *{duration} • {model}*"
```

With provider and tool calls:

```yaml
template: "-# *{duration} • ctx {ctx_pct} • {tokens} • tools:{tool_calls} • {model} • {provider}*"
```

Debug-only session ID:

```yaml
template: "-# *{duration} • {model} • session:{session_id}*"
```

## How it works

1. Hooks into `post_api_request` to collect per-turn stats.
2. Appends a follow-up Discord message with the rendered template.
3. Reads `config.yaml` on first use and caches it for the session.

## Security notes

- Treat `{session_id}` as private/debug metadata.
- Avoid exposing internal counters or session information in public channels.
- Use a private channel or a separate template for debugging if needed.

## Compatibility

- Works with Hermes installations that support the Discord platform.
- If the internal adapter changes, the plugin may need an update.

## Enabling and disabling

- **Enable:** place this repository in your Hermes plugins directory.
- **Disable:** remove the symlink or directory.

## Requirements

- Hermes Agent with Discord platform support
- Python dependencies required by the plugin
