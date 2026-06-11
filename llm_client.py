import json
import urllib.request
import urllib.error

def call_llm_api_stream(prompt: str, config: dict):
    """
    Calls the OpenAI-compatible LLM endpoint and yields tokens (streaming)
    using the standard library urllib to avoid new dependencies.
    """
    api_key = config.get("API_KEY", "")
    base_url = config.get("BASE_URL", "").rstrip("/")
    model = config.get("MODEL", "llama-3.3-70b-versatile")
    
    if not api_key:
        yield "⚠️ API Key is not set yet! Use `/apikey <key>` to set it."
        return
        
    if not base_url:
        yield "⚠️ Base URL is not set. Use `/baseurl <url>` to set it."
        return

    system_instruction = (
        "You are MCQ Copilot, a friendly and intelligent AI assistant built into the MCQ Batch Converter app. "
        "Your goal is to assist users with file conversions, explain concepts, and provide helpful guidance. "
        "CRITICAL: This chat UI does NOT support Markdown. Do NOT use asterisks (**) for bold, or underscores (_) for italics. "
        "Keep your answers plain text, clear, concise, and engaging. You can use emojis to express emotions! "
        "If the user asks to convert, remind them they can click the Convert button or use quick actions. "
        "Always reply in English."
    )

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
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
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        err_code = e.code
        err_msg = e.reason
        try:
            body = e.read().decode('utf-8')
            parsed_err = json.loads(body)
            err_msg = parsed_err.get("error", {}).get("message", err_msg)
        except Exception:
            pass

        if err_code == 429:
            yield f"⚠️ API Rate Limit Exceeded (HTTP 429):\n\n{err_msg}"
        elif err_code == 403:
            yield "❌ Forbidden (HTTP 403): Access denied. Please ensure your API key and base URL are correct."
        elif err_code == 401:
            yield "❌ Unauthorized (HTTP 401): Invalid API Key."
        else:
            yield f"❌ Error {err_code}: {err_msg}"
    except Exception as e:
        yield f"Error communicating with LLM API: {str(e)}"
