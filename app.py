from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import uuid
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "smartcalc-pro-secret-key-change-this"

MAX_HISTORY = 50