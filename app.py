from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import uuid
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "smartcalc-pro-secret-key-change-this"

MAX_HISTORY = 50

CURRENCY_RATES_IDR = {
    "IDR": 1.0,
    "USD": 15750.0,
    "EUR": 17150.0,
    "SGD": 11600.0,
    "JPY": 105.0,
    "MYR": 3550.0,
    "AUD": 10400.0,
    "GBP": 19850.0,
}

BASES = {
    "binary": 2,
    "octal": 8,
    "decimal": 10,
    "hexadecimal": 16,
}

TEMP_UNITS = ("C", "F", "K", "R")

def now_str() -> str:
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def ensure_history():
    if "history" not in session:
        session["history"] = []

def push_history(item: dict):
    ensure_history()
    history = session["history"]
    history.insert(0, item)
    session["history"] = history[:MAX_HISTORY]
    session.modified = True


def format_number(n):
    if isinstance(n, bool):
        return "1" if n else "0"
    if isinstance(n, int):
        return f"{n:,}".replace(",", ".")
    if isinstance(n, float):
        if abs(n - round(n)) < 1e-12:
            return f"{int(round(n)):,}".replace(",", ".")
        s = f"{n:.10f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") if "," not in s else s
    return str(n)

def build_history_item(module, title, formula, result_display):
    return {
        "id": str(uuid.uuid4()),
        "time": now_str(),
        "module": module,
        "title": title,
        "formula": formula,
        "result": result_display,
    }

def decimal_to_base_steps(number: int, base: int):
    if number == 0:
        return ["0 dibagi apa pun tetap 0."]
    steps = []
    n = abs(number)
    digits = "0123456789ABCDEF"
    remainders = []
    while n > 0:
        q, r = divmod(n, base)
        steps.append(f"{n} ÷ {base} = {q} sisa {digits[r]}")
        remainders.append(digits[r])
        n = q
    converted = "".join(reversed(remainders))
    if number < 0:
        converted = "-" + converted
    steps.append(f"Baca sisa dari bawah ke atas: {converted}")
    return steps

def base_to_decimal_expression(value: str, from_base: int):
    value = value.strip().upper()
    sign = -1 if value.startswith("-") else 1
    if value.startswith("-"):
        value = value[1:]
    digits = "0123456789ABCDEF"
    total = 0
    parts = []
    for idx, ch in enumerate(reversed(value)):
        if ch not in digits[:from_base]:
            raise ValueError(f"Karakter '{ch}' tidak valid untuk basis {from_base}.")
        d = digits.index(ch)
        power = idx
        term = d * (from_base ** power)
        parts.append(f"{d}×{from_base}^{power}={term}")
        total += term
    total *= sign
    return total, " + ".join(reversed(parts))

def convert_base(value: str, from_name: str, to_name: str):
    if from_name not in BASES or to_name not in BASES:
        raise ValueError("Basis tidak valid.")
    from_base = BASES[from_name]
    to_base = BASES[to_name]
    decimal_value, expansion = base_to_decimal_expression(value, from_base)

    steps = [
        f"Nilai awal: {value} pada basis {from_base}.",
        f"Uraikan ke desimal: {expansion}.",
        f"Hasil ke desimal: {decimal_value}.",
    ]

    if to_base == 10:
        converted = str(decimal_value)
        steps.append("Karena basis tujuan desimal, hasil akhir sama dengan nilai desimal.")
    else:
        base_steps = decimal_to_base_steps(decimal_value, to_base)
        converted = base_steps[-1].split(": ", 1)[-1]
        steps.extend([f"Konversi desimal ke basis {to_base}:"] + base_steps[:-1] + [base_steps[-1]])

    formula = f"{value}_{from_base} = {converted}_{to_base}"
    return converted, formula, steps

def convert_temperature(value: float, from_unit: str, to_unit: str):
    f = from_unit.upper()
    t = to_unit.upper()
    if f not in TEMP_UNITS or t not in TEMP_UNITS:
        raise ValueError("Satuan suhu tidak valid.")

    def to_celsius(v, unit):
        if unit == "C":
            return v, f"{v}°C langsung ke Celsius."
        if unit == "F":
            return (v - 32) * 5 / 9, f"({v} - 32) × 5/9"
        if unit == "K":
            return v - 273.15, f"{v} - 273.15"
        if unit == "R":
            return v * 5 / 4, f"{v} × 5/4"

    def from_celsius(c, unit):
        if unit == "C":
            return c, f"{c}°C"
        if unit == "F":
            return c * 9 / 5 + 32, f"({c} × 9/5) + 32"
        if unit == "K":
            return c + 273.15, f"{c} + 273.15"
        if unit == "R":
            return c * 4 / 5, f"{c} × 4/5"

    celsius, step1 = to_celsius(value, f)
    result, step2 = from_celsius(celsius, t)

    formula_map = {
        ("C", "F"): "F = (C × 9/5) + 32",
        ("C", "K"): "K = C + 273.15",
        ("C", "R"): "R = C × 4/5",
        ("F", "C"): "C = (F - 32) × 5/9",
        ("F", "K"): "K = (F - 32) × 5/9 + 273.15",
        ("F", "R"): "R = (F - 32) × 4/9",
        ("K", "C"): "C = K - 273.15",
        ("K", "F"): "F = (K - 273.15) × 9/5 + 32",
        ("K", "R"): "R = (K - 273.15) × 4/5",
        ("R", "C"): "C = R × 5/4",
        ("R", "F"): "F = (R × 9/4) + 32",
        ("R", "K"): "K = (R × 5/4) + 273.15",
    }
    formula = formula_map.get((f, t), f"Konversi dari {f} ke {t}")
    steps = [
        f"Nilai awal: {value}°{f}.",
        f"Langkah 1 ke Celsius: {step1}.",
        f"Langkah 2 ke tujuan: {step2}.",
    ]
    return result, formula, steps

def convert_currency(amount: float, from_cur: str, to_cur: str):
    f = from_cur.upper()
    t = to_cur.upper()
    if f not in CURRENCY_RATES_IDR or t not in CURRENCY_RATES_IDR:
        raise ValueError("Mata uang tidak didukung.")
    idr_value = amount * CURRENCY_RATES_IDR[f]
    result = idr_value / CURRENCY_RATES_IDR[t]
    formula = f"{amount} {f} × rate_{f} ÷ rate_{t} = {result:.6f} {t}"
    steps = [
        f"Rate statis: 1 {f} = {CURRENCY_RATES_IDR[f]:,.2f} IDR.".replace(",", "."),
        f"Ubah ke IDR: {amount} × {CURRENCY_RATES_IDR[f]:,.2f} = {idr_value:,.2f} IDR.".replace(",", "."),
        f"Ubah ke {t}: {idr_value:,.2f} ÷ {CURRENCY_RATES_IDR[t]:,.2f} = {result:.6f} {t}".replace(",", "."),
    ]
    return result, formula, steps