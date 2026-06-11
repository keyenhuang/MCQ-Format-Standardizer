import json
from pathlib import Path

# Try to import keyring for secure API Key storage
try:
    import keyring
except ImportError:
    keyring = None

CONFIG_FILE = Path("config.json")
_CONFIG_CACHE = None

def get_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config = {
        "API_KEY": "",
        "BASE_URL": "https://api.groq.com/openai/v1",
        "MODEL": "llama-3.3-70b-versatile"
    }

    # Load from config.json if it exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("BASE_URL"):
                    config["BASE_URL"] = data["BASE_URL"].strip()
                if data.get("MODEL"):
                    config["MODEL"] = data["MODEL"].strip()
                if data.get("API_KEY"):
                    config["API_KEY"] = data["API_KEY"].strip()
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}")

    # Try to load API key from keyring if available
    if keyring:
        try:
            stored_key = keyring.get_password("MCQConverterApp", "API_KEY")
            if stored_key:
                config["API_KEY"] = stored_key.strip()
        except Exception as e:
            print(f"Warning: Failed to read from keyring: {e}")

    _CONFIG_CACHE = config
    return config

def save_config_value(key_name, value):
    global _CONFIG_CACHE
    config = get_config()
    value_stripped = value.strip() if isinstance(value, str) else value

    if key_name == "API_KEY" and keyring:
        try:
            keyring.set_password("MCQConverterApp", "API_KEY", value_stripped)
            # Remove plain API key from config.json for security if it was there
            _save_to_json_file("API_KEY", "")
            if _CONFIG_CACHE is not None:
                _CONFIG_CACHE["API_KEY"] = value_stripped
            return True
        except Exception as e:
            print(f"Warning: Failed to write to keyring: {e}. Falling back to file storage.")

    # Fallback/Default: save to json
    success = _save_to_json_file(key_name, value_stripped)
    if success and _CONFIG_CACHE is not None:
        _CONFIG_CACHE[key_name] = value_stripped
    return success

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
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
