from flask import Flask, jsonify, render_template, request
import os
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Demo-only state for initial scaffold
accounts = {
    "demo": {"balance": 5000.00, "currency": "USD"},
    "live": {"balance": 0.00, "currency": "USD"},
}

trades = []
market = {
    "symbol": "DIGIT-USD",
    "last": 487.42,
    "open": 482.1,
    "high": 491.7,
    "low": 479.2,
    "history": [480, 482, 481, 486, 489, 485, 488, 494, 492, 487, 490, 487.42],
}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/market")
def api_market():
    return jsonify({
        "symbol": market["symbol"],
        "last": market["last"],
        "open": market["open"],
        "high": market["high"],
        "low": market["low"],
        "history": market["history"],
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.post("/api/demo-trade")
def demo_trade():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "matches")
    digit = int(data.get("digit", 0))
    amount = float(data.get("amount", 0.0))
    prediction = data.get("prediction", "match")
    account_name = data.get("account", "demo")

    if account_name not in accounts:
        return jsonify({"error": "Unknown account type."}), 400
    if not 0 <= digit <= 9:
        return jsonify({"error": "Digit must be between 0 and 9."}), 400
    if amount <= 0:
        return jsonify({"error": "Trade amount must be greater than zero."}), 400

    # Simulated result for demo environment only
    result_digit = sum(int(n) for n in str(int(market["last"] * 100))) % 10
    result = {
        "matches": result_digit == digit,
        "differs": result_digit != digit,
        "even": result_digit % 2 == 0,
        "odd": result_digit % 2 != 0,
    }

    if mode == "matches":
        won = result["matches"] if prediction == "match" else result["differs"]
    elif mode == "even_odd":
        won = result["even"] if prediction == "even" else result["odd"]
    else:
        won = True

    payout = amount * 1.9 if won else 0.0
    accounts[account_name]["balance"] = round(accounts[account_name]["balance"] + payout - amount, 2)

    trade = {
        "id": len(trades) + 1,
        "timestamp": datetime.utcnow().isoformat(),
        "mode": mode,
        "digit": digit,
        "prediction": prediction,
        "amount": amount,
        "result_digit": result_digit,
        "won": won,
        "payout": round(payout, 2),
        "balance_after": accounts[account_name]["balance"],
    }
    trades.append(trade)

    return jsonify({
        "success": True,
        "trade": trade,
        "account": accounts[account_name],
        "note": "Demo trading is simulated only. Live trading is not enabled.",
    })


@app.get("/api/trades")
def api_trades():
    return jsonify({"trades": trades[-10:][::-1]})


@app.get("/api/admin")
def api_admin():
    return jsonify({
        "users": 128,
        "demo_accounts": 92,
        "live_accounts": 0,
        "daily_volume": 0,
        "status": "demo-only",
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok", "mode": "demo"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
