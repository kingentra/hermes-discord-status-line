"""status-line plugin: send a configurable Discord status line after each response."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = "> -# *{duration} ⋅ {ctx_pct} ⋅ {tokens} ⋅ {model}*"
_config_cache: Dict[str, Any] | None = None
_accumulator: Dict[str, Any] = {}
_sending_followup = False
_PATCHED = False
_orig_send: Any = None
_ctx_window_cache: Dict[str, int] = {}


def _load_config() -> Dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    cfg_path = Path(__file__).parent / "config.yaml"
    try:
        with open(cfg_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    _config_cache = data
    return data


def _get_template() -> str:
    return _load_config().get("template", _DEFAULT_TEMPLATE)


def reload_config() -> None:
    global _config_cache
    _config_cache = None


def _reset() -> None:
    _accumulator.clear()


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


def _fmt_tokens(count: int) -> str:
    if count >= 1_000_000:
        return f"{count // 1_000_000}M"
    if count >= 1_000:
        val = count / 1_000
        return f"{val:.0f}K" if val >= 10 else f"{val:.1f}K"
    return str(count)


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s}s"
    h, remainder = divmod(int(seconds), 3600)
    m = remainder // 60
    return f"{h}h {m}m"


def _format_ctx_pct(input_tokens: int, ctx_window: int) -> str:
    if not ctx_window:
        return "?%"
    pct = (input_tokens / ctx_window) * 100 if ctx_window else 0.0
    if input_tokens > 0 and pct < 1:
        return "<1%"
    if pct < 10:
        return "0%" if input_tokens == 0 else f"{pct:.1f}%"
    return f"{pct:.0f}%"


async def _send_followup(self, chat_id: str, line: str, metadata: Any) -> None:
    """Send the status line as a bare follow-up message."""
    global _sending_followup
    _sending_followup = True
    try:
        await _orig_send(self, chat_id, line, reply_to=None, metadata=metadata)
    except Exception:
        logger.warning("status-line: failed to send follow-up", exc_info=True)
    finally:
        _sending_followup = False


def _apply_patch() -> None:
    """Import DiscordAdapter and apply the send-patch lazily."""
    global _PATCHED, _orig_send
    try:
        from hermes_plugins.discord_platform.adapter import DiscordAdapter
    except ImportError:
        return

    _orig_send = DiscordAdapter.send

    async def _patched_send(self, chat_id, content, reply_to=None, metadata=None):
        global _sending_followup
        result = await _orig_send(self, chat_id, content, reply_to, metadata)
        if result.success and not _sending_followup:
            line = _build_status_line()
            if line:
                await _send_followup(self, chat_id, line, metadata)
        return result

    DiscordAdapter.send = _patched_send
    _PATCHED = True
    logger.info("status-line: DiscordAdapter.send patched (deferred)")


def _on_post_api_request(**kwargs) -> None:
    if not _PATCHED:
        _apply_patch()

    _accumulator["total_duration"] = _accumulator.get("total_duration", 0.0) + float(kwargs.get("api_duration", 0))
    _accumulator["last_usage"] = kwargs.get("usage")
    _accumulator["last_model"] = kwargs.get("response_model") or kwargs.get("model", "?")
    _accumulator["last_provider"] = kwargs.get("provider", "")
    _accumulator["call_count"] = _accumulator.get("call_count", 0) + 1
    _accumulator["finish_reason"] = kwargs.get("finish_reason", "")
    _accumulator["message_count"] = kwargs.get("message_count", 0)
    _accumulator["tool_call_count"] = kwargs.get("assistant_tool_call_count", 0)
    _accumulator["content_chars"] = kwargs.get("assistant_content_chars", 0)
    _accumulator["session_id"] = kwargs.get("session_id", "")


def _build_status_line() -> str:
    """Read and clear the accumulator. Return formatted status line or ''."""
    stats = dict(_accumulator)
    _reset()

    if not stats or not stats.get("last_model"):
        return ""

    duration = _fmt_duration(stats["total_duration"])
    usage = stats.get("last_usage") or {}
    input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", 0) or 0
    cache_read = usage.get("cache_read_tokens", 0) or 0
    provider = stats.get("last_provider", "")
    model = stats.get("last_model", "?")

    ctx_window = _get_context_window(provider, model)
    if ctx_window and input_tokens is not None:
        ctx_pct = _format_ctx_pct(int(input_tokens), ctx_window)
        tokens = f"( {_fmt_tokens(int(input_tokens))}/{_fmt_tokens(ctx_window)} )"
    else:
        ctx_pct = "?%"
        tokens = ""

    if "/" in model and not model.startswith("/"):
        model = model.split("/")[-1]

    call_count = str(stats.get("call_count", 1))
    finish_reason = stats.get("finish_reason") or ""
    msg_count = str(stats.get("message_count", 0))
    tool_calls = str(stats.get("tool_call_count", 0))
    chars = _fmt_tokens(stats.get("content_chars", 0))
    cache_pct = f"{int(cache_read / input_tokens * 100)}%" if cache_read and input_tokens else ""

    variables = {
        "duration": duration,
        "ctx_pct": ctx_pct,
        "tokens": tokens,
        "model": model,
        "call_count": call_count,
        "input_tokens": _fmt_tokens(int(input_tokens)),
        "output_tokens": _fmt_tokens(int(output_tokens)),
        "total_tokens": _fmt_tokens(int(total_tokens)),
        "cache_pct": cache_pct,
        "finish_reason": finish_reason,
        "msg_count": msg_count,
        "tool_calls": tool_calls,
        "chars": chars,
        "provider": provider,
        "session_id": stats.get("session_id", ""),
    }

    template = _get_template()
    try:
        return template.format_map(variables)
    except Exception:
        return _DEFAULT_TEMPLATE.format_map(variables)


def register(ctx) -> None:
    ctx.register_hook("post_api_request", _on_post_api_request)
    logger.debug("status-line: post_api_request hook registered")
