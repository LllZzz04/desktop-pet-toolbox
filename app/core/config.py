from dataclasses import asdict, dataclass
from pathlib import Path

from .storage import read_json, write_json


@dataclass
class Config:
    screenshot_hotkey: str = "Alt+A"
    quick_ocr_hotkey: str = "Alt+Shift+A"
    restore_pins: bool = True
    fullscreen_dnd: bool = True
    history_limit: int = 50
    auto_copy: bool = True
    startup: bool = False  # Interface reserved; v0.1 does not modify startup entries.
    pet_position: list[int] | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    translation_model: str = "qwen2.5:3b"
    translation_language: str = "zh-CN"
    chat_base_url: str = "https://api.deepseek.com"
    chat_model: str = "deepseek-flash"
    chat_save_history: bool = True

    @classmethod
    def load(cls, directory: Path):
        raw = read_json(directory / "config.json", {})
        cfg = cls()
        if not isinstance(raw, dict):
            return cfg
        if isinstance(raw.get("screenshot_hotkey"), str):
            cfg.screenshot_hotkey = raw["screenshot_hotkey"]
        if type(raw.get("history_limit")) is int:
            cfg.history_limit = max(1, min(50, raw["history_limit"]))
        if type(raw.get("auto_copy")) is bool:
            cfg.auto_copy = raw["auto_copy"]
        if type(raw.get("restore_pins")) is bool:
            cfg.restore_pins = raw["restore_pins"]
        if type(raw.get("fullscreen_dnd")) is bool:
            cfg.fullscreen_dnd = raw["fullscreen_dnd"]
        for field in ("ollama_url", "translation_model", "translation_language", "chat_base_url", "chat_model",
                      "quick_ocr_hotkey"):
            if isinstance(raw.get(field), str):
                setattr(cfg, field, raw[field])
        if type(raw.get("chat_save_history")) is bool:
            cfg.chat_save_history = raw["chat_save_history"]
        position = raw.get("pet_position")
        if isinstance(position, list) and len(position) == 2 and all(type(x) is int for x in position):
            cfg.pet_position = position
        return cfg

    def save(self, directory: Path):
        write_json(directory / "config.json", asdict(self))
