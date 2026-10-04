"""Chat settings and limits, independent of widgets and network access."""
from urllib.parse import urlsplit, urlunsplit

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
MODEL_CHOICES = ("deepseek-flash", "deepseek-v4-pro")
MAX_INPUT_CHARS = 8000
MAX_ANSWER_CHARS = 60000
MAX_CONTEXT_CHARS = 32000
MAX_CONTEXT_TURNS = 12
MAX_HISTORY_CHARS = 200000
MAX_HISTORY_TURNS = 100


def validate_chat_settings(base_url, model):
    base_url, model = base_url.strip().rstrip("/"), model.strip()
    if not base_url or len(base_url) > 500 or any(c.isspace() for c in base_url):
        raise ValueError("请填写有效的对话服务地址")
    try:
        url = urlsplit(base_url)
        port = url.port
    except ValueError as error:
        raise ValueError("对话服务地址格式不正确") from error
    if (url.scheme != "https" or not url.hostname or url.username is not None
            or url.password is not None or url.query or url.fragment
            or (port is not None and not 1 <= port <= 65535)):
        raise ValueError("对话服务地址需为 HTTPS 地址，不能包含账号、密码或查询参数")
    if not model or len(model) > 160 or any(c.isspace() for c in model):
        raise ValueError("请填写有效的对话模型名称")
    path = url.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[:-len("/chat/completions")]
    return urlunsplit((url.scheme, url.netloc, path, "", "")), model


def validate_api_key(key):
    key = key.strip()
    if len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("API Key 格式不正确，请只粘贴平台提供的密钥")
    return key
