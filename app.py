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