"""Account-free, privacy-first local storage in ~/.agrishield/: profile, farm ledger and cached forecast."""
import json
import os
from datetime import date, datetime
from pathlib import Path

DIR = Path.home() / ".agrishield"
DEFAULTS = dict(name="", lang="ar", place="Alger", lat=36.75, lon=3.06, crops=[], animals=[], area=1.0,
                notify=False, price=dict(hay=35, barley=55, bran=40))


def load(name, default):
    try:
        return json.loads((DIR / f"{name}.json").read_text("utf-8"))
    except Exception:
        return default


def save(name, data):
    """Atomic write so a crash never leaves a half-written file."""
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = DIR / f"{name}.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    os.replace(tmp, DIR / f"{name}.json")


def load_profile():
    """Saved profile merged over defaults, so files written by older versions never miss a key."""
    saved = load("profile", {})
    p = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    if isinstance(saved, dict):
        p.update(saved)
    return p


def add_entry(kind, cat, amount, note=""):
    """Append a ledger entry: kind 'in' (income) or 'out' (expense)."""
    j = load("journal", [])
    j.append(dict(date=str(date.today()), type=kind, cat=cat, amount=float(amount), note=note))
    save("journal", j)


def ledger_summary(entries):
    inc = sum(e["amount"] for e in entries if e["type"] == "in")
    exp = sum(e["amount"] for e in entries if e["type"] == "out")
    return inc, exp, inc - exp


def greeting(t):
    h = datetime.now().hour
    if h < 12:
        return t("صباح الخير", "Bonjour", "Good morning")
    return t("مساء الخير", "Bon après-midi", "Good afternoon") if h < 18 else t("مساء النور", "Bonsoir", "Good evening")
