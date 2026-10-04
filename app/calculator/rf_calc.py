"""Series-component Q, exact series/parallel conversion, and VCO FoM.

No evaluation, GUI, networking or persistence. Formula references are in
RF_CALC.md. FoM uses the negative convention with Pdc normalized to 1 mW.
"""
import math
import re

from .lc_calc import format_engineering
from .unit_converter import NUMBER, QUANTITY, quantity

HELP = (
    "射频计算（本机执行）\n\n"
    "rf q 6GHz 1nH 2ohm\n→ 电感串联 Q；也支持电容\n\n"
    "rf rp 6GHz 1nH Q=20\n→ 等效 Rp、Rs 与并联 Lp\n\n"
    "rf rp 6GHz 1nH 2ohm\n→ 由串联损耗电阻求 Rp\n\n"
    "rf fom 6GHz 1MHz -120dBc/Hz 10mW\n→ 载波、偏移、相噪、直流功耗\n\n"
    "Rp 为指定频率的串并联等效值，L/C 为串联元件值。"
    "FoM 使用负值惯例；功耗为直流功耗。"
)


def positive(value, name):
    if not math.isfinite(value) or not 1e-30 <= value <= 1e30:
        raise ValueError(f"{name} 需为正数，SI 值范围为 1e-30～1e30")
    return value


def normalize(text):
    text = re.sub(r"\s*=\s*", "=", text.strip())
    # Allow spaces between numbers and units without swallowing the next label.
    return re.sub(r"(?<=\d)\s+([A-Za-zµμΩ]+)(?=\s|$)", r"\1", text)


def component_values(text):
    values = {}
    for token in normalize(text).split():
        match = re.fullmatch(rf"(?:(f|l|c|rs|q)=)?({NUMBER})([A-Za-zµμΩ]+)?", token, re.IGNORECASE)
        if not match:
            raise ValueError("参数格式：6GHz 1nH 2ohm 或 6GHz 1nH Q=20")
        name = (match[1] or "").lower()
        if name == "q":
            if match[3]:
                raise ValueError("Q 是无单位数值，例如 Q=20")
            key, value = "q", float(match[2])
        else:
            if not match[3]:
                raise ValueError("频率、电感、电容和电阻需要明确单位")
            item = quantity(match[2], match[3])
            key, value = item.dimension, item.si
            expected = {"f": "frequency", "l": "inductance", "c": "capacitance", "rs": "resistance"}
            if name and expected.get(name) != key:
                raise ValueError(f"{name} 的单位类型不正确")
            if key not in expected.values():
                raise ValueError("仅支持频率、电感、电容、串联电阻和 Q")
        if key in values:
            raise ValueError("同一类型参数不能重复")
        values[key] = positive(value, key)
    reactive = set(values) & {"inductance", "capacitance"}
    if "frequency" not in values or len(reactive) != 1:
        raise ValueError("需要一个频率和一个电感或电容")
    dimension = reactive.pop()
    omega = 2 * math.pi * values["frequency"]
    reactance = omega * values[dimension] if dimension == "inductance" else 1 / (omega * values[dimension])
    return values, dimension, reactance


def calculate_component(kind, text):
    values, dimension, reactance = component_values(text)
    if kind == "q":
        if "resistance" not in values or "q" in values:
            raise ValueError("Q 格式：rf q 6GHz 1nH 2ohm（最后为高频串联损耗电阻）")
        q = reactance / values["resistance"]
        if not math.isfinite(q):
            raise ValueError("Q 结果超出支持范围")
        formula = "Q = 2πfLs / Rs" if dimension == "inductance" else "Q = 1 / (2πfCsRs)"
        return f"Q = {q:.8g}\n{formula}\n串联元件模型；Rs 为该频率下的损耗电阻"
    if ("q" in values) == ("resistance" in values):
        raise ValueError("Rp 需要 Q=数值或串联电阻之一，例如 rf rp 6GHz 1nH Q=20")
    q = values.get("q", 0) or reactance / values["resistance"]
    rs = reactance / q
    rp = rs * (1 + q * q)
    parallel = values[dimension] * (1 + 1 / (q * q)) if dimension == "inductance" else (
        values[dimension] / (1 + 1 / (q * q)))
    if any(not math.isfinite(v) or v <= 0 for v in (q, rs, rp, parallel)):
        raise ValueError("串并联转换结果超出支持范围")
    symbol = "Lp" if dimension == "inductance" else "Cp"
    return (f"Rp = {format_engineering(rp, 'resistance')}\n"
            f"Rs = {format_engineering(rs, 'resistance')} · Q = {q:.8g}\n"
            f"{symbol} = {format_engineering(parallel, dimension)}\n"
            "Rp = Rs(1 + Q²)，指定频率下的精确串并联等效")


def calculate_fom(text):
    pattern = (rf"(?:f0=)?{QUANTITY}\s+(?:df=)?{QUANTITY}\s+"
               rf"(?:pn=)?({NUMBER})(?:\s*dBc/Hz)?\s+(?:p=)?{QUANTITY}")
    match = re.fullmatch(pattern, normalize(text), re.IGNORECASE)
    if not match:
        raise ValueError("FoM 格式：rf fom 6GHz 1MHz -120dBc/Hz 10mW")
    carrier, offset, power = quantity(match[1], match[2]), quantity(match[3], match[4]), quantity(match[6], match[7])
    if carrier.dimension != "frequency" or offset.dimension != "frequency" or power.dimension != "power":
        raise ValueError("FoM 参数依次为载波频率、偏移频率、相噪和直流功耗")
    f0, df, pdc = positive(carrier.si, "载波"), positive(offset.si, "偏移"), positive(power.si, "功耗")
    noise = float(match[5])
    if df >= f0:
        raise ValueError("偏移频率需小于载波频率")
    if not math.isfinite(noise) or not -1000 <= noise <= 0:
        raise ValueError("相噪需为 -1000～0 dBc/Hz 的数值")
    fom = noise - 20 * math.log10(f0 / df) + 10 * math.log10(pdc / 1e-3)
    return (f"FoM = {fom:.8g} dBc/Hz\n"
            f"反号表示：{-fom:.8g} dB\n"
            "FoM = PN − 20log₁₀(f₀/Δf) + 10log₁₀(Pdc/1mW)\n"
            "负值惯例下越小越好；不含调谐范围修正")


def calculate_rf(text):
    parts = text.strip().split(maxsplit=1)
    kind, body = parts[0].lower() if parts else "help", parts[1] if len(parts) > 1 else ""
    if kind == "help":
        return HELP
    if kind in ("q", "rp"):
        return calculate_component(kind, body)
    if kind == "fom":
        return calculate_fom(body)
    raise ValueError("射频命令支持 rf q、rf rp、rf fom、rf help")
