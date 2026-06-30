"""
app.py – Web dashboard entry point for the crypto trading bot.

Run:  python app.py
Open: http://localhost:5000

The trading loop runs in a background thread.
Flask serves the dashboard and a JSON API polled every 3 s by the browser.
"""

import re
import threading
import time
from collections import deque
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template

import exchange
import strategy
import trader
import logger
import config

app = Flask(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────
_log: deque = deque(maxlen=60)
_prices: dict = {}
_signals: dict = {}
_signal_reasons: dict = {}
_balance_usdt: float | None = None
_top_pairs: list[str] = []
_btc_filter_status: str = "UNKNOWN"
_lock = threading.Lock()
_bot_active: bool = True   # controlled by Start/Stop buttons

_RICH_TAG = re.compile(r"\[/?[a-zA-Z0-9_/ ]+\]")


def _strip(s: str) -> str:
    """Remove Rich markup tags so plain text goes to the web UI."""
    return _RICH_TAG.sub("", s).strip()


def _classify(raw: str) -> str:
    r = raw.lower()
    if "close_tp" in r:                     return "tp"
    if "close_sl" in r:                     return "sl"
    if "buy" in r:                           return "buy"
    if "error" in r:                         return "error"
    if "skip" in r or "insufficient" in r:   return "warn"
    return "info"


def _add_log(raw: str) -> None:
    entry = {
        "time":  datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "msg":   _strip(raw),
        "level": _classify(raw),
    }
    with _lock:
        _log.appendleft(entry)


def _drain() -> None:
    while trader.event_log:
        _add_log(trader.event_log.popleft())


def _fetch_and_compute(symbol: str, timeframe: str):
    df = exchange.fetch_ohlcv(symbol, timeframe=timeframe)
    return strategy.compute_indicators(df)


def _is_btc_bullish() -> bool:
    btc_df = _fetch_and_compute(config.BTC_FILTER_SYMBOL, config.BTC_FILTER_TIMEFRAME)
    if len(btc_df) < strategy.min_required_candles():
        return False
    curr = btc_df.iloc[-1]
    if curr[["ema_fast", "ema_slow"]].isna().any():
        return False
    return bool(curr["ema_fast"] > curr["ema_slow"])


def _rank_watchlist() -> tuple[list[str], list[dict]]:
    ranked: list[dict] = []

    for symbol in config.WATCHLIST:
        try:
            df = _fetch_and_compute(symbol, config.RANKING_TIMEFRAME)
            metrics = strategy.compute_strength_metrics(df)
            if not metrics:
                continue
            ranked.append({"symbol": symbol, **metrics})
        except Exception as exc:
            _add_log(f"RANK SKIP [{symbol}] {exc}")

    ranked.sort(key=lambda row: row["score"], reverse=True)
    top_pairs = [row["symbol"] for row in ranked[:config.TOP_PAIRS_COUNT]]
    return top_pairs, ranked


# ── Background trading loop ───────────────────────────────────────────────────

def _trading_loop() -> None:
    global _bot_active, _balance_usdt, _top_pairs, _btc_filter_status

    last_candle: dict = {}
    selected_pairs: list[str] = list(config.WATCHLIST[:config.TOP_PAIRS_COUNT])
    last_rank_refresh = 0.0
    last_balance_refresh = 0.0
    btc_bullish = False
    _top_pairs = selected_pairs

    _add_log(f"Bot started — watchlist: {', '.join(config.WATCHLIST)}  [{config.TIMEFRAME}]")

    while True:
        with _lock:
            active = _bot_active

        now_ts = time.time()

        if now_ts - last_rank_refresh >= config.RANKING_REFRESH_SECONDS:
            selected_pairs, ranked = _rank_watchlist()
            last_rank_refresh = now_ts
            if selected_pairs:
                with _lock:
                    _top_pairs = selected_pairs
                _add_log(f"Top pairs refreshed: {', '.join(selected_pairs)}")
            else:
                _add_log("Ranking returned no symbols; keeping previous top list")

        if now_ts - last_balance_refresh >= config.BALANCE_REFRESH_SECONDS:
            try:
                bal = exchange.get_balance("USDT")
                with _lock:
                    _balance_usdt = bal
            except Exception as exc:
                _add_log(f"Balance fetch failed: {exc}")
            last_balance_refresh = now_ts

        if config.ENABLE_BTC_MARKET_FILTER:
            try:
                btc_bullish = _is_btc_bullish()
            except Exception as exc:
                btc_bullish = False
                _add_log(f"BTC filter fallback to bearish: {exc}")
        else:
            btc_bullish = True

        with _lock:
            _btc_filter_status = "BULLISH" if btc_bullish else "BEARISH"

        managed_symbols = sorted(set(selected_pairs) | set(trader.get_all_positions().keys()))

        for symbol in managed_symbols:
            try:
                df           = _fetch_and_compute(symbol, config.TIMEFRAME)
                htf_df       = _fetch_and_compute(symbol, config.TREND_TIMEFRAME)
                price        = float(df.iloc[-1]["close"])
                candle_time  = df.index[-1]
                new_candle   = candle_time != last_candle.get(symbol)

                # Always update prices for display, even when paused
                with _lock:
                    _prices[symbol] = price

                if active:
                    trader.check_exit_on_price(price, symbol)
                    _drain()

                    if new_candle:
                        last_candle[symbol] = candle_time
                        sig, reason = strategy.get_signal_with_reason(df, htf_df)

                        if symbol not in selected_pairs:
                            sig = strategy.Signal.HOLD
                            reason = "Not in top-ranked pairs"

                        if (
                            sig == strategy.Signal.BUY
                            and config.ENABLE_BTC_MARKET_FILTER
                            and not btc_bullish
                        ):
                            _add_log(f"SKIP [{symbol}] BTC 4h trend is bearish")
                            sig = strategy.Signal.HOLD
                            reason = "BTC market filter is bearish"

                        atr_value = float(df.iloc[-1].get("atr", 0.0))
                        trader.execute(sig, price, symbol, atr_value)
                        _drain()

                        with _lock:
                            _signals[symbol] = sig.value
                            _signal_reasons[symbol] = reason

                        _add_log(f"{symbol}  {sig.value}  @ {price:.2f}")

            except Exception as exc:
                _add_log(f"ERROR [{symbol}]: {exc}")

        time.sleep(config.POLL_INTERVAL_SECONDS)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        symbols=config.WATCHLIST,
        timeframe=config.TIMEFRAME,
        testnet=config.USE_TESTNET,
    )


@app.route("/api/control", methods=["POST"])
def api_control():
    global _bot_active
    from flask import request
    action = request.get_json(force=True).get("action")
    log_msg = None
    with _lock:
        if action == "start" and not _bot_active:
            _bot_active = True
            log_msg = "Bot [green]started[/green] by user"
        elif action == "stop" and _bot_active:
            _bot_active = False
            log_msg = "Bot [yellow]stopped[/yellow] by user"
        current = _bot_active
    # _add_log must be called OUTSIDE the lock (it acquires the lock itself)
    if log_msg:
        _add_log(log_msg)
    return jsonify({"bot_active": current})


@app.route("/api/data")
def api_data():
    with _lock:
        prices  = dict(_prices)
        signals = dict(_signals)
        signal_reasons = dict(_signal_reasons)
        log     = list(_log)
        balance = _balance_usdt
        top_pairs = list(_top_pairs)
        btc_filter_status = _btc_filter_status

    positions_raw  = trader.get_all_positions()
    open_positions = []
    for sym, pos in positions_raw.items():
        cur = prices.get(sym, pos["entry_price"])
        pnl = round((cur - pos["entry_price"]) * pos["qty"], 4)
        open_positions.append({
            "symbol":        sym,
            "entry_price":   pos["entry_price"],
            "current_price": cur,
            "qty":           pos["qty"],
            "stop_loss":     pos["stop_loss"],
            "take_profit":   pos["take_profit"],
            "pnl":           pnl,
        })

    history       = logger.get_history(limit=25)
    closed        = [t for t in history if t.get("pnl_usdt") is not None]
    total_pnl     = round(sum(t["pnl_usdt"] for t in closed), 4)
    wins          = sum(1 for t in closed if t["pnl_usdt"] > 0)
    win_rate      = round(wins / len(closed) * 100, 1) if closed else 0.0

    with _lock:
        bot_active = _bot_active

    return jsonify({
        "time":           datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "bot_active":     bot_active,
        "balance_usdt":   balance,
        "top_pairs":      top_pairs,
        "btc_filter":     btc_filter_status,
        "open_positions": open_positions,
        "history":        history,
        "log":            log,
        "signals":        signals,
        "signal_reasons": signal_reasons,
        "prices":         prices,
        "stats": {
            "total_pnl":    total_pnl,
            "total_trades": len(closed),
            "wins":         wins,
            "win_rate":     win_rate,
            "open_count":   len(open_positions),
        },
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.init_db()
    logger.clear_history()
    t = threading.Thread(target=_trading_loop, daemon=True)
    t.start()
    print("=" * 52)
    print("  Crypto Trading Bot – Listening on 0.0.0.0:8080")
    print("  Dashboard  →  http://localhost:8080 (or your server IP:8080)")
    print("  Press Ctrl+C to stop")
    print("=" * 52)
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
