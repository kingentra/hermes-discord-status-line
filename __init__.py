"""status-line -- sends a customizable status line as a separate Discord
message after each response.

Template is configured in config.yaml alongside this file.
Available variables: {duration}, {ctx_pct}, {tokens}, {model}, {call_count}

Default template:
    -# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}*

Enable/disable: load or unload the plugin. Plugin exists = enabled.
Remove from ~/.hermes/plugins/ to disable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATE = "-# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}*"
_config_cache: Dict[str, Any] | None = None


def _load_config() -> Dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    cfg_path = Path(__file__).parent / "config.yaml"
    try:
        with open(cfg_path) as f:
            data = yaml.safe_load(f) or {}
        _config_cache = data
    except Exception:
        data = {}
    return data


def _get_template() -> str:
    return _load_config().get("template", _DEFAULT_TEMPLATE)


def reload_config() -> None:
    global _config_cache
    _config_cache = None

# ---------------------------------------------------------------------------
# Accumulator
# ---------------------------------------------------------------------------

_accumulator: Dict[str, Any] = {}

# Re-entrancy guard: the follow-up send also goes through the monkey-patch
_sending_followup: bool = False


def _reset() -> None:
    _accumulator.clear()


# ---------------------------------------------------------------------------
# Context window lookup (cached per model)
# ---------------------------------------------------------------------------

_ctx_window_cache: Dict[str, int] = {}


def _get_context_window(provider: str, model: str) -> int:
    cache_key = f"{provider}/{model}"
    if cache_key in _ctx_window_cache:
        return _ctx_window_cache[cache_key]

    try:
        from agent.models_dev import get_model_capabilities
        caps = get_model_capabilities(provider, model)
        window = caps.context_window if caps else 0
    except Exception:
        window = 0

    _ctx_window_cache[cache_key] = window
    return window


# ---------------------------------------------------------------------------
# Token formatting
# ---------------------------------------------------------------------------


def _fmt_tokens(count: int) -> str:
    if count >= 1_000_000:
        return f"{count // 1_000_000}M"
    if count >= 1_000:
        val = count / 1_000
        return f"{val:.0f}K" if val >= 10 else f"{val:.1f}K"
    return str(count)


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s}s"
    h, remainder = divmod(int(seconds), 3600)
    m = remainder // 60
    return f"{h}h {m}m"


# ---------------------------------------------------------------------------
# Hook handler
# ---------------------------------------------------------------------------


def _on_post_api_request(**kwargs) -> None:
    _accumulator["total_duration"] = _accumulator.get("total_duration", 0.0) + float(kwargs.get("api_duration", 0))
    _accumulator["last_usage"] = kwargs.get("usage")
    _accumulator["last_model"] = kwargs.get("response_model") or kwargs.get("model", "?")
    _accumulator["last_provider"] = kwargs.get("provider", "")
    _accumulator["call_count"] = _accumulator.get("call_count", 0) + 1


# ---------------------------------------------------------------------------
# Status line builder
# ---------------------------------------------------------------------------


def _build_status_line() -> str:
    """Read and clear the accumulator. Return formatted status line or ''."""
    stats = dict(_accumulator)
    _reset()

    if not stats or not stats.get("last_model"):
        return ""

    duration = _fmt_duration(stats["total_duration"])

    usage = stats.get("last_usage") or {}
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    provider = stats.get("last_provider", "")
    model = stats.get("last_model", "?")

    ctx_window = _get_context_window(provider, model)
    if ctx_window and prompt_tokens:
        ctx_pct = f"{int(prompt_tokens / ctx_window * 100)}%"
        tokens = f"( {_fmt_tokens(prompt_tokens)}/{_fmt_tokens(ctx_window)} )"
    else:
        ctx_pct = "?%"
        tokens = ""

    if "/" in model and not model.startswith("/"):
        model = model.split("/")[-1]

    call_count = str(stats.get("call_count", 1))

    variables = {
        "duration": duration,
        "ctx_pct": ctx_pct,
        "tokens": tokens,
        "model": model,
        "call_count": call_count,
    }

    template = _get_template()
    try:
        return template.format_map(variables)
    except Exception:
        return _DEFAULT_TEMPLATE.format_map(variables)


# ---------------------------------------------------------------------------
# Plugin registration -- hook + monkey-patch
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    ctx.register_hook("post_api_request", _on_post_api_request)

    # Monkey-patch DiscordAdapter.send to send status line as a follow-up
    try:
        from hermes_plugins.discord_platform.adapter import DiscordAdapter
    except ImportError:
        logger.warning("status-line: DiscordAdapter not found, skipping monkey-patch")
        return

    _orig_send = DiscordAdapter.send

    async def _patched_send(self, chat_id, content, reply_to=None, metadata=None):
        nonlocal _orig_send
        global _sending_followup

        # Call original send to deliver the main message
        result = await _orig_send(self, chat_id, content, reply_to, metadata)

        # Send follow-up status line if response succeeded and we have stats
        if result.success and not _sending_followup:
            line = _build_status_line()
            if line:
                _sending_followup = True
                try:
                    # Send to same place, no reply (bare status line)
                    await _orig_send(self, chat_id, line, reply_to=None, metadata=metadata)
                except Exception:
                    logger.warning("status-line: failed to send follow-up", exc_info=True)
                finally:
                    _sending_followup = False

        return result

    DiscordAdapter.send = _patched_send
    logger.info("status-line: plugin registered + DiscordAdapter.send patched")
