from flask import Flask, jsonify, render_template, request, session
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "omega_tradehub.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DEFAULT_MARKET = {
    "symbol": "DIGIT-USD",
    "last": 487.42,
    "open": 482.1,
    "high": 491.7,
    "low": 479.2,
    "history": [480, 482, 481, 486, 489, 485, 488, 494, 492, 487, 490, 487.42],
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                demo_balance REAL NOT NULL DEFAULT 5000.0,
                live_balance REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                digit INTEGER,
                prediction TEXT NOT NULL,
                amount REAL NOT NULL,
                result_digit INTEGER,
                account_mode TEXT NOT NULL DEFAULT 'demo',
                won INTEGER NOT NULL DEFAULT 0,
                payout REAL NOT NULL DEFAULT 0.0,
                balance_after REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                last REAL NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                history TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        demo_user = conn.execute("SELECT id FROM users WHERE username = ?", ("demo",)).fetchone()
        if demo_user is None:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role, demo_balance, live_balance) VALUES (?, ?, ?, ?, ?, ?)",
                ("demo", "demo@omegatradehub.local", generate_password_hash("demo123"), "demo", 5000.0, 0.0),
            )

        admin_user = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if admin_user is None:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role, demo_balance, live_balance) VALUES (?, ?, ?, ?, ?, ?)",
                ("admin", "admin@omegatradehub.local", generate_password_hash("admin123"), "admin", 15000.0, 0.0),
            )

        market_exists = conn.execute("SELECT id FROM market LIMIT 1").fetchone()
        if market_exists is None:
            conn.execute(
                "INSERT INTO market (symbol, last, open, high, low, history) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    DEFAULT_MARKET["symbol"],
                    DEFAULT_MARKET["last"],
                    DEFAULT_MARKET["open"],
                    DEFAULT_MARKET["high"],
                    DEFAULT_MARKET["low"],
                    json.dumps(DEFAULT_MARKET["history"]),
                ),
            )


with app.app_context():
    init_db()


def user_to_dict(user_row):
    if user_row is None:
        return None
    return {
        "id": user_row["id"],
        "username": user_row["username"],
        "email": user_row["email"],
        "role": user_row["role"],
        "demo_balance": round(float(user_row["demo_balance"]), 2),
        "live_balance": round(float(user_row["live_balance"]), 2),
        "created_at": user_row["created_at"],
    }


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row


def get_market_snapshot():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM market ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return DEFAULT_MARKET.copy()
    history = json.loads(row["history"]) if row["history"] else DEFAULT_MARKET["history"]
    return {
        "symbol": row["symbol"],
        "last": float(row["last"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "history": history,
        "timestamp": row["created_at"],
    }


def seed_market_history(new_history):
    with get_db() as conn:
        last = new_history[-1]
        high = max(new_history)
        low = min(new_history)
        open_value = new_history[0]
        conn.execute(
            "INSERT INTO market (symbol, last, open, high, low, history) VALUES (?, ?, ?, ?, ?, ?)",
            (DEFAULT_MARKET["symbol"], last, open_value, high, low, json.dumps(new_history)),
        )


def compute_trade_result(mode, digit, prediction, threshold=None):
    market = get_market_snapshot()
    market_base = int(round(float(market["last"]) * 100))
    result_digit = (market_base + (len(market["history"]) * 17)) % 10

    if mode == "matches":
        matches = result_digit == digit
        differs = result_digit != digit
        won = matches if prediction == "match" else differs
    elif mode == "even_odd":
        even = result_digit % 2 == 0
        odd = result_digit % 2 != 0
        won = even if prediction == "even" else odd
    elif mode == "over_under":
        threshold = int(threshold if threshold is not None else 5)
        above = result_digit > threshold
        below = result_digit < threshold
        won = above if prediction == "above" else below
    else:
        won = False

    return result_digit, won


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "mode": "demo", "database": str(DB_PATH)})


@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters long."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if not email:
        return jsonify({"error": "Email is required."}), 400

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
        if existing:
            return jsonify({"error": "A user with that username or email already exists."}), 409

        user_id = conn.execute(
            "INSERT INTO users (username, email, password_hash, role, demo_balance, live_balance) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, generate_password_hash(password), "user", 5000.0, 0.0),
        ).lastrowid

        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    session["user_id"] = user["id"]
    return jsonify({"success": True, "message": "Account created successfully.", "user": user_to_dict(user)})


@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username.lower()),
        ).fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        return jsonify({"success": True, "message": "Login successful.", "user": user_to_dict(user)})

    return jsonify({"error": "Invalid username or password."}), 401


@app.post("/api/logout")
def api_logout():
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Logged out."})


@app.get("/api/session")
def api_session():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "user": user_to_dict(user)})


@app.get("/api/market")
def api_market():
    return jsonify(get_market_snapshot())


@app.post("/api/trade")
@app.post("/api/demo-trade")
def api_trade():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Please register or log in before placing a trade."}), 401

    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "matches")
    account_mode = data.get("account", "demo")
    prediction = data.get("prediction", "match")
    amount = float(data.get("amount", 0.0))
    digit = int(data.get("digit", 0))
    threshold = int(data.get("threshold", 5))

    if account_mode != "demo":
        return jsonify({"error": "Live trading is disabled. Demo mode is active only until provider verification and compliance checks are complete."}), 403

    if amount <= 0:
        return jsonify({"error": "Trade amount must be greater than zero."}), 400
    if not 0 <= digit <= 9:
        return jsonify({"error": "Digit must be between 0 and 9."}), 400

    with get_db() as conn:
        current = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    if current["demo_balance"] < amount:
        return jsonify({"error": "Insufficient demo balance for this trade."}), 400

    result_digit, won = compute_trade_result(mode, digit, prediction, threshold)
    payout = amount * 1.9 if won else 0.0
    balance_after = round(float(current["demo_balance"]) + payout - amount, 2)

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET demo_balance = ? WHERE id = ?",
            (balance_after, user["id"]),
        )
        trade_id = conn.execute(
            "INSERT INTO trades (user_id, mode, digit, prediction, amount, result_digit, account_mode, won, payout, balance_after) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user["id"],
                mode,
                digit,
                prediction,
                amount,
                result_digit,
                account_mode,
                1 if won else 0,
                round(payout, 2),
                balance_after,
            ),
        ).lastrowid

        trade = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()

    updated_user = get_current_user()
    market = get_market_snapshot()
    history = market["history"]
    history = history[-11:] + [result_digit]
    history = history[-12:]
    seed_market_history(history)

    return jsonify(
        {
            "success": True,
            "trade": {
                "id": trade["id"],
                "mode": trade["mode"],
                "digit": trade["digit"],
                "prediction": trade["prediction"],
                "amount": round(float(trade["amount"]), 2),
                "result_digit": trade["result_digit"],
                "won": bool(trade["won"]),
                "payout": round(float(trade["payout"]), 2),
                "balance_after": round(float(trade["balance_after"]), 2),
                "timestamp": trade["created_at"],
            },
            "account": user_to_dict(updated_user),
            "message": "Demo trade executed in simulated mode only.",
        }
    )


@app.get("/api/trades")
def api_trades():
    user = get_current_user()
    if not user:
        return jsonify({"trades": []})

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user["id"],),
        ).fetchall()

    trades = []
    for row in rows:
        trades.append(
            {
                "id": row["id"],
                "mode": row["mode"],
                "digit": row["digit"],
                "prediction": row["prediction"],
                "amount": round(float(row["amount"]), 2),
                "result_digit": row["result_digit"],
                "won": bool(row["won"]),
                "payout": round(float(row["payout"]), 2),
                "balance_after": round(float(row["balance_after"]), 2),
                "timestamp": row["created_at"],
            }
        )

    return jsonify({"trades": trades[::-1]})


@app.get("/api/admin")
def api_admin():
    user = get_current_user()
    if not user or user["role"] != "admin":
        return jsonify({"error": "Admin access required."}), 403

    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        demo_accounts = conn.execute("SELECT COUNT(*) FROM users WHERE demo_balance > 0").fetchone()[0]
        live_accounts = conn.execute("SELECT COUNT(*) FROM users WHERE live_balance > 0").fetchone()[0]
        total_volume = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM trades").fetchone()[0]
        recent_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

    return jsonify(
        {
            "users": total_users,
            "demo_accounts": demo_accounts,
            "live_accounts": live_accounts,
            "daily_volume": round(float(total_volume), 2),
            "total_trades": recent_trades,
            "status": "demo-only",
            "note": "Live trading and deposits remain disabled until provider authorization and Kenyan compliance review are complete.",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)


# Security note: this scaffold intentionally avoids live deposits, withdrawals, and provider integrations.
# Only simulated demo trading is available until a verified provider, risk controls, and legal review are complete.
