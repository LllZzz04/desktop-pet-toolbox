"""LC resonance only; independent of UI and future RF calculators."""
import math
import re

from .unit_converter import QUANTITY, quantity

ENGINEERING_UNITS = {
    "frequency": [(1, "Hz"), (1e3, "kHz"), (1e6, "MHz"), (1e9, "GHz"), (1e12, "THz")],
    "capacitance": [(1e-15, "fF"), (1e-12, "pF"), (1e-9, "nF"), (1e-6, "uF"), (1e-3, "mF"), (1, "F")],
    "inductance": [(1e-12, "pH"), (1e-9, "nH"), (1e-6, "uH"), (1e-3, "mH"), (1, "H")],
    "resistance": [(1e-3, "mΩ"), (1, "Ω"), (1e3, "kΩ"), (1e6, "MΩ")],
}


def format_engineering(value, dimension):
    units = ENGINEERING_UNITS[dimension]
    factor, unit = units[0]
    for scale, candidate in units:
        if value >= scale:
            factor, unit = scale, candidate
    return f"{value / factor:.5g} {unit}"


def solve_lc(first, second):
    if first.dimension == second.dimension:
        raise ValueError("LC 计算需要频率、电感、电容中的两种不同参数")
    values = {first.dimension: first.si, second.dimension: second.si}
    if not set(values).issubset({"frequency", "inductance", "capacitance"}):
        raise ValueError("LC 计算仅支持频率、电感、电容")
    if any(not 1e-30 <= value <= 1e30 for value in values.values()):
        raise ValueError("LC 参数必须为正数，且处于 1e-30 至 1e30 的 SI 范围")
    if "frequency" not in values:
        dimension, symbol = "frequency", "f"
        result = 1 / (2 * math.pi * math.sqrt(values["inductance"]) * math.sqrt(values["capacitance"]))
    else:
        dimension = "capacitance" if "inductance" in values else "inductance"
        symbol = "C" if dimension == "capacitance" else "L"
        known = values.get("inductance", values.get("capacitance"))
        result = (1 / (2 * math.pi * values["frequency"])) ** 2 / known
    if not math.isfinite(result) or result <= 0:
        raise ValueError("LC 结果超出支持范围")
    return f"{symbol} = {format_engineering(result, dimension)}"


def calculate_lc(text):
    match = re.fullmatch(rf"\s*{QUANTITY}\s+{QUANTITY}\s*", text)
    if not match:
        raise ValueError("LC 格式：6GHz 1nH、6GHz 700fF 或 1nH 700fF")
    return solve_lc(quantity(match[1], match[2]), quantity(match[3], match[4]))
