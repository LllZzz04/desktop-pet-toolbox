"""Command routing, with no UI imports or storage side effects."""
import re
from dataclasses import dataclass

from .lc_calc import calculate_lc
from .math_calc import CONSTANTS, FUNCTIONS, calculate
from .unit_converter import QUANTITY, convert
from .rf_calc import calculate_rf


@dataclass(frozen=True)
class CommandResult:
    kind: str
    text: str
    ok: bool = True


class CommandParser:
    @staticmethod
    def _looks_like_math(text):
        # A failed calculator expression stays a local error. Natural-language
        # questions, including English containing "to", go to chat instead.
        if re.search(r"[\u3400-\u9fff]", text):
            return False
        if re.fullmatch(r"[\d\s.eE+\-*/^()%\[\]{},=]+", text):
            return True
        if re.match(r"\s*[A-Za-z_]\w*\s*\(", text):
            return True
        if re.match(r"\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*[+\-*/^%=]", text):
            return True
        names = re.findall(r"[A-Za-z_]\w*", text)
        return bool(names) and all(name in FUNCTIONS or name in CONSTANTS for name in names)

    def parse(self, text):
        text = text.strip()
        if not text:
            return CommandResult("empty", "")
        if len(text) > 8000:
            return CommandResult("error", "输入过长（最多 8000 字符）", False)
        try:
            rf = re.fullmatch(r"/?rf(?:\s+(.*))?", text, re.IGNORECASE | re.DOTALL)
            if rf:
                body = rf[1] or "help"
                return CommandResult("help" if body.strip().lower() == "help" else "calculation",
                                     calculate_rf(body))
            if text == "/chat" or text.startswith("/chat ") or text.startswith("/chat\t"):
                return CommandResult("chat", text[5:].strip())
            if text == "/note" or text.startswith("/note ") or text.startswith("/note\t"):
                content = text[5:].strip()
                if not content:
                    raise ValueError("请在 /note 后输入便签内容")
                return CommandResult("note", content)
            if text.startswith("/"):
                raise ValueError("未知命令，可使用 /note 内容、/chat 或 /rf help")
            if re.fullmatch(rf"\s*{QUANTITY}\s+to(?:\s+[a-zA-ZµμΩ]+)?\s*", text):
                return CommandResult("calculation", convert(text))
            if re.fullmatch(rf"\s*{QUANTITY}\s+{QUANTITY}\s*", text):
                return CommandResult("calculation", calculate_lc(text))
            try:
                return CommandResult("calculation", f"{calculate(text):.12g}")
            except (ValueError, OverflowError):
                if self._looks_like_math(text):
                    raise
                return CommandResult("chat", text)
        except (ValueError, OverflowError) as error:
            return CommandResult("error", str(error), False)
