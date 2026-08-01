import json
import urllib.request
import urllib.error

from logger import get_logger
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_AGENT

logger = get_logger()
REQUEST_TIMEOUT = 30



def call_llm_api_stream(prompt: str, config: dict):
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
        "messages": [
            {"role": "system", "content": config.get("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)},
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {api_key}",
            'Accept': 'text/event-stream',
            'User-Agent': config.get("USER_AGENT", DEFAULT_USER_AGENT),
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            while True:
                line = response.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                if line_str.startswith("data: "):
                    data_content = line_str[6:]
                    if data_content == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_content)
                        choices = chunk.get("choices", [{}])
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        pass

    except urllib.error.HTTPError as e:
        err_code = e.code
        err_msg = str(e.reason)
        try:
            body = e.read().decode('utf-8')
            parsed = json.loads(body)
            err_detail = parsed.get("error", {}).get("message", "")
            if err_detail:
                err_msg = err_detail
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        friendly = {
            429: f"API Rate Limit Exceeded (HTTP 429):\n\n{err_msg}",
            403: "Forbidden (HTTP 403): Access denied. Please ensure your API key and base URL are correct.",
            401: "Unauthorized (HTTP 401): Invalid API Key.",
        }
        yield friendly.get(err_code, f"Error {err_code}: {err_msg}")
        logger.warning("LLM API HTTP %s: %s", err_code, err_msg)

    except (urllib.error.URLError, OSError) as e:
        msg = f"Network error communicating with LLM API: {e}"
        yield msg
        logger.warning(msg)
    except Exception as e:
        msg = f"Unexpected error communicating with LLM API: {e}"
        yield msg
        logger.exception(msg)
