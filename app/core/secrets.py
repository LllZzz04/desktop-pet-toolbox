"""Store the chat API key with Windows DPAPI, never in ordinary config JSON."""
import base64
import ctypes
import os
from ctypes import wintypes

from .storage import read_json, write_json


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data, *, protect):
    if os.name != "nt":
        raise OSError("API Key 的加密保存目前需要 Windows")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    incoming = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = _Blob()
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    second_type = wintypes.LPCWSTR if protect else ctypes.POINTER(wintypes.LPWSTR)
    function.argtypes = [ctypes.POINTER(_Blob), second_type, ctypes.POINTER(_Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    function.restype = wintypes.BOOL
    # DPAPI binds the encrypted blob to the current Windows user. Forbid a
    # system prompt so a save failure stays an ordinary application error.
    if not function(ctypes.byref(incoming), "DesktopPetToolbox Chat API" if protect else None,
                    None, None, None, 1, ctypes.byref(outgoing)):
        raise OSError("Windows 无法加密或读取 API Key，请在设置中重新填写")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel32.LocalFree(ctypes.cast(outgoing.data, ctypes.c_void_p))


class ChatCredentials:
    def __init__(self, directory):
        self.path = directory / "chat_key.json"

    def load(self):
        if self.path.exists() and self.path.stat().st_size > 64_000:
            raise OSError("无法读取已保存的 API Key，请在对话设置中重新填写")
        raw = read_json(self.path, None)
        if raw is None:
            return ""
        try:
            if not isinstance(raw, dict) or raw.get("version") != 1:
                raise ValueError
            encrypted = base64.b64decode(raw["encrypted_key"], validate=True)
            if not encrypted or len(encrypted) > 20000:
                raise ValueError
            return _crypt(encrypted, protect=False).decode("utf-8")
        except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
            raise OSError("无法读取已保存的 API Key，请在对话设置中重新填写") from error

    def save(self, key):
        if not key:
            self.path.unlink(missing_ok=True)
            return
        encrypted = _crypt(key.encode("utf-8"), protect=True)
        write_json(self.path, {"version": 1,
                             "encrypted_key": base64.b64encode(encrypted).decode("ascii")})
