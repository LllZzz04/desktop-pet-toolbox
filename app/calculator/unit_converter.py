import math
import re
from dataclasses import dataclass


UNITS = {
    "mm": ("length", 1e-3), "cm": ("length", 1e-2), "m": ("length", 1),
    "inch": ("length", .0254), "ft": ("length", .3048),
    "Hz": ("frequency", 1), "kHz": ("frequency", 1e3),
    "MHz": ("frequency", 1e6), "GHz": ("frequency", 1e9),
    "ns": ("time", 1e-9), "us": ("time", 1e-6), "ms": ("time", 1e-3), "s": ("time", 1),
    "fF": ("capacitance", 1e-15), "pF": ("capacitance", 1e-12),
    "nF": ("capacitance", 1e-9), "uF": ("capacitance", 1e-6),
    "pH": ("inductance", 1e-12), "nH": ("inductance", 1e-9), "uH": ("inductance", 1e-6),
    "ohm": ("resistance", 1), "Ohm": ("resistance", 1), "Ω": ("resistance", 1),
    "mohm": ("resistance", 1e-3), "mΩ": ("resistance", 1e-3),
    "kohm": ("resistance", 1e3), "kOhm": ("resistance", 1e3), "kΩ": ("resistance", 1e3),
    "Mohm": ("resistance", 1e6), "MOhm": ("resistance", 1e6), "MΩ": ("resistance", 1e6),
    "uW": ("power", 1e-6), "mW": ("power", 1e-3), "W": ("power", 1),
}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
QUANTITY = rf"({NUMBER})\s*([a-zA-ZµμΩ]+)"


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    dimension: str
    si: float


def quantity(value, unit):
    unit = unit.replace("µ", "u").replace("μ", "u")
    if unit not in UNITS:
        raise ValueError(f"不支持单位 {unit}（单位区分大小写）")
    dimension, factor = UNITS[unit]
    value = float(value)
    si = value * factor
    if not math.isfinite(value) or not math.isfinite(si) or abs(value) > 1e100:
        raise ValueError("数值超出支持范围")
    return Quantity(value, unit, dimension, si)


def convert(text):
    match = re.fullmatch(rf"\s*{QUANTITY}\s+to\s+([a-zA-ZµμΩ]+)\s*", text)
    if not match:
        raise ValueError("换算格式：25 mm to inch")
    source = quantity(match[1], match[2])
    target = quantity(1, match[3])
    if source.dimension != target.dimension:
        raise ValueError("不能换算不同类型的单位")
    result = source.si / target.si
    if not math.isfinite(result):
        raise ValueError("结果超出支持范围")
    return f"{result:.10g} {target.unit}"
