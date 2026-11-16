import json
import threading
import urllib.request
import urllib.error
from typing import List, Optional

from logger import get_logger
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_AGENT

logger = get_logger()
REQUEST_TIMEOUT = 30


def _build_messages(prompt: str, config: dict, history: Optional[List[dict]] = None) -> List[dict]:
    system_prompt = config.get("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    if prompt:
        messages.append({"role": "user", "content": prompt})
    return messages


def _format_http_error(e: urllib.error.HTTPError) -> str:
    err_code = e.code
    err_msg = str(e.reason)
    try:
        body = e.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        err_detail = parsed.get("error", {}).get("message", "")
        if err_detail:
            err_msg = err_detail
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass

    friendly = {
        429: f"API Rate Limit Exceeded (HTTP 429):\n\n{err_msg}",
        403: "Forbidden (HTTP 403): Access denied. Please ensure your API key and base URL are correct.",
        401: "Unauthorized (HTTP 401): Invalid API Key.",
    }
    return friendly.get(err_code, f"Error {err_code}: {err_msg}")


def _parse_sse_line(line_bytes: bytes) -> Optional[str]:
    line_str = line_bytes.decode("utf-8", errors="replace").strip()
    if not line_str or not line_str.startswith("data:"):
        return None
    data_content = line_str[5:].lstrip()
    if data_content == "[DONE]":
        return "__DONE__"
    try:
        chunk = json.loads(data_content)
        choices = chunk.get("choices") or [{}]
        delta = choices[0].get("delta", {})
        return delta.get("content", "") or ""
    except (json.JSONDecodeError, IndexError, KeyError, AttributeError):
        return None


def call_llm_api_stream(
    prompt: str,
    config: dict,
    history: Optional[List[dict]] = None,
    cancel_event: Optional[threading.Event] = None,
):
    api_key = config.get("API_KEY", "")
    base_url = config.get("BASE_URL", "").rstrip("/")
    model = config.get("MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        yield "API Key is not set yet! Use `/apikey <key>` to set it."
        return

    if not base_url:
        yield "Base URL is not set. Use `/baseurl <url>` to set it."
        return

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": _build_messages(prompt, config, history),
        "stream": True,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
            "User-Agent": config.get("USER_AGENT", DEFAULT_USER_AGENT),
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            while True:
                if cancel_event and cancel_event.is_set():
                    break
                line = response.readline()
                if not line:
                    break
                token = _parse_sse_line(line)
                if token == "__DONE__":
                    break
                if token:
                    yield token

    except urllib.error.HTTPError as e:
        msg = _format_http_error(e)
        yield msg
        logger.warning("LLM API HTTP %s: %s", e.code, msg)
    except (urllib.error.URLError, OSError) as e:
        msg = f"Network error communicating with LLM API: {e}"
        yield msg
        logger.warning(msg)
    except Exception as e:
        msg = f"Unexpected error communicating with LLM API: {e}"
        yield msg
        logger.exception(msg)

