import json
import os
from pathlib import Path

from logger import get_logger

try:
    import keyring
except ImportError:
    keyring = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    load_dotenv = None

CONFIG_FILE = Path("config.json")
_CONFIG_CACHE = None
logger = get_logger()

DEFAULT_SYSTEM_PROMPT = (
    "You are MCQ Copilot, a friendly and intelligent AI assistant built into the MCQ Format Standardizer app. "
    "Your goal is to assist users with file conversions, explain concepts, and provide helpful guidance. "
    "CRITICAL: This chat UI does NOT support Markdown. Do NOT use asterisks (**) for bold, "
    "or underscores (_) for italics. "
    "Keep your answers plain text, clear, concise, and engaging. You can use emojis to express emotions! "
    "If the user asks to convert, remind them they can click the Convert button or use quick actions. "
    "Always reply in English."
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _apply_env_overrides(config):
    env_key = os.environ.get("MCQ_API_KEY") or os.environ.get("API_KEY")
    if env_key:
        config["API_KEY"] = env_key.strip()
    env_url = os.environ.get("MCQ_BASE_URL") or os.environ.get("BASE_URL")
    if env_url:
        config["BASE_URL"] = env_url.strip()
    env_model = os.environ.get("MCQ_MODEL") or os.environ.get("MODEL")
    if env_model:
        config["MODEL"] = env_model.strip()


def get_config():
    cached = _CONFIG_CACHE
    if cached is not None:
        return cached

    global _CONFIG_CACHE

    config = {
        "API_KEY": "",
        "BASE_URL": "https://api.groq.com/openai/v1",
        "MODEL": "llama-3.3-70b-versatile",
        "SYSTEM_PROMPT": os.environ.get("MCQ_SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT,
        "USER_AGENT": os.environ.get("MCQ_USER_AGENT") or DEFAULT_USER_AGENT,
    }

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("BASE_URL"):
                config["BASE_URL"] = data["BASE_URL"].strip()
            if data.get("MODEL"):
                config["MODEL"] = data["MODEL"].strip()
            api_key_from_file = data.get("API_KEY", "").strip()
            if api_key_from_file:
                logger.warning("API key found in plaintext config.json. Consider using keyring or .env for better security.")
                config["API_KEY"] = api_key_from_file
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load config.json: %s", e)

    if keyring:
        try:
            stored_key = keyring.get_password("MCQFormatStandardizer", "API_KEY")
            if stored_key:
                config["API_KEY"] = stored_key.strip()
        except Exception as e:
            logger.warning("Failed to read from keyring: %s", e)

    _apply_env_overrides(config)

    _CONFIG_CACHE = config
    return config


def save_config_value(key_name, value):
    config = get_config()
    value_stripped = value.strip() if isinstance(value, str) else value

    if key_name == "API_KEY" and keyring:
        try:
            keyring.set_password("MCQFormatStandardizer", "API_KEY", value_stripped)
            _remove_from_json_file("API_KEY")
            if _CONFIG_CACHE is not None:
                _CONFIG_CACHE["API_KEY"] = value_stripped
            return True
        except Exception as e:
            logger.warning("Failed to write to keyring: %s. Falling back to file storage.", e)

    success = _save_to_json_file(key_name, value_stripped)
    if success and _CONFIG_CACHE is not None:
        _CONFIG_CACHE[key_name] = value_stripped
    return success


def _remove_from_json_file(key_name):
    try:
        data = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.pop(key_name, None)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Error removing key from config file: %s", e)


def _save_to_json_file(key_name, value):
    try:
        data = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[key_name] = value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Error saving config: %s", e)
        return False
