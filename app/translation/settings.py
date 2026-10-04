import ipaddress
from urllib.parse import urlsplit, urlunsplit

LANGUAGES = {"zh-CN": "简体中文", "zh-TW": "繁體中文", "en": "English",
             "ja": "日本語", "ko": "한국어"}
PROMPT_LANGUAGES = {"zh-CN": "Simplified Chinese", "zh-TW": "Traditional Chinese",
                    "en": "English", "ja": "Japanese", "ko": "Korean"}


def validate_translation_settings(endpoint, model, language):
    endpoint, model = endpoint.strip(), model.strip()
    try:
        parsed = urlsplit(endpoint)
        host, port = parsed.hostname, parsed.port
        if host == "localhost":
            host = "127.0.0.1"
        if (parsed.scheme not in ("http", "https") or not host
            or not ipaddress.ip_address(host).is_loopback or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError()
    except ValueError as error:
        raise ValueError("Ollama 地址必须是本机地址，例如 http://127.0.0.1:11434") from error
    if not model or len(model) > 160 or any(character.isspace() or ord(character) < 32 for character in model):
        raise ValueError("请输入有效的本地模型名称，例如 qwen2.5:3b")
    if "cloud" in model.rsplit(":", 1)[-1].lower():
        raise ValueError("图片翻译仅支持本地模型，请选择已下载的非 cloud 模型")
    if language not in LANGUAGES:
        raise ValueError("请选择支持的目标语言")
    host_part = f"[{host}]" if ":" in host else host
    netloc = f"{host_part}:{port}" if port is not None else host_part
    return urlunsplit((parsed.scheme, netloc, "", "", "")), model, language
