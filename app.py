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