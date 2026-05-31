from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "health_tracker.db"
SUPPLEMENTS = ["Vitamin D", "Omega-3", "Magnesium", "Multivitamin"]
WATER_TARGET_LITERS = 2.5
WATER_STEP_LITERS = 0.25

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS daily_status (
                day TEXT PRIMARY KEY,
                water_liters REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS weight_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                weight_kg REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS supplement_status (
                day TEXT NOT NULL,
                supplement TEXT NOT NULL,
                taken INTEGER NOT NULL CHECK(taken IN (0, 1)),
                PRIMARY KEY (day, supplement)
            );
            """
        )


@app.before_request
def ensure_db() -> None:
    init_db()


def get_today() -> str:
    return date.today().isoformat()


def upsert_daily_status(day: str, water_liters: float) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO daily_status (day, water_liters)
            VALUES (?, ?)
            ON CONFLICT(day) DO UPDATE SET water_liters = excluded.water_liters
            """,
            (day, water_liters),
        )


def get_water_for_day(day: str) -> float:
    with get_db() as conn:
        row = conn.execute(
            "SELECT water_liters FROM daily_status WHERE day = ?", (day,)
        ).fetchone()
        return float(row["water_liters"]) if row else 0.0


def get_busy_days_count() -> int:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM (
                SELECT day FROM daily_status WHERE water_liters > 0
                UNION
                SELECT day FROM weight_entries
                UNION
                SELECT day FROM supplement_status
            )
            """
        ).fetchone()
        return int(row["cnt"])


def get_weight_history(limit: int = 30) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT day, weight_kg
            FROM weight_entries
            ORDER BY day ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def get_supplement_status_for_day(day: str) -> dict[str, bool]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT supplement, taken FROM supplement_status WHERE day = ?",
            (day,),
        ).fetchall()
    existing = {row["supplement"]: bool(row["taken"]) for row in rows}
    return {supplement: existing.get(supplement, False) for supplement in SUPPLEMENTS}


@app.route("/")
def dashboard():
    today = get_today()
    water_liters = get_water_for_day(today)
    busy_days = get_busy_days_count()
    weight_history = get_weight_history()
    supplements_today = get_supplement_status_for_day(today)
    taken_count = sum(1 for taken in supplements_today.values() if taken)

    chart_labels = [entry["day"] for entry in weight_history]
    chart_values = [entry["weight_kg"] for entry in weight_history]

    return render_template(
        "dashboard.html",
        busy_days=busy_days,
        water_liters=water_liters,
        water_target=WATER_TARGET_LITERS,
        water_percent=min(100, (water_liters / WATER_TARGET_LITERS) * 100),
        supplements_today=supplements_today,
        taken_count=taken_count,
        total_supplements=len(SUPPLEMENTS),
        chart_labels=json.dumps(chart_labels),
        chart_values=json.dumps(chart_values),
    )


@app.post("/water")
def update_water():
    direction = request.form.get("direction", "plus")
    today = get_today()
    current = get_water_for_day(today)

    if direction == "minus":
        updated = max(0.0, current - WATER_STEP_LITERS)
    else:
        updated = current + WATER_STEP_LITERS

    upsert_daily_status(today, round(updated, 2))
    return redirect(url_for("dashboard"))


@app.post("/weight")
def add_weight():
    raw_weight = request.form.get("weight_kg", "").strip()
    if not raw_weight:
        return redirect(url_for("dashboard"))

    try:
        weight = float(raw_weight)
    except ValueError:
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO weight_entries (day, weight_kg) VALUES (?, ?)",
            (get_today(), weight),
        )

    return redirect(url_for("dashboard"))


@app.route("/supplements", methods=["GET", "POST"])
def supplements():
    today = get_today()

    if request.method == "POST":
        with get_db() as conn:
            for supplement in SUPPLEMENTS:
                taken_value = 1 if request.form.get(supplement) == "taken" else 0
                conn.execute(
                    """
                    INSERT INTO supplement_status (day, supplement, taken)
                    VALUES (?, ?, ?)
                    ON CONFLICT(day, supplement)
                    DO UPDATE SET taken = excluded.taken
                    """,
                    (today, supplement, taken_value),
                )
        return redirect(url_for("dashboard"))

    status = get_supplement_status_for_day(today)
    return render_template("supplements.html", supplements=status)


if __name__ == "__main__":
    app.run(debug=True)
