"""
exchange.py – Binance Testnet wrapper using ccxt.
Provides: fetch_ohlcv, get_balance, place_market_order.
"""

import os
import ccxt
import pandas as pd
from dotenv import load_dotenv
import config

load_dotenv()


def _build_exchange() -> ccxt.binance:
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "adjustForTimeDifference": True,
        },
    })
    if config.USE_TESTNET:
        exchange.set_sandbox_mode(True)
    return exchange


# Module-level singleton so we don't re-build on every call
_exchange: ccxt.binance = _build_exchange()


# ──────────────────────────────────────────────────────────────────────────────

def fetch_ohlcv(symbol: str = config.SYMBOL,
                timeframe: str = config.TIMEFRAME,
                limit: int = config.CANDLES) -> pd.DataFrame:
    """Return the last `limit` closed candles as a DataFrame."""
    raw = _exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 1)
    # Drop the last (still-open) candle
    raw = raw[:-1]
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    return df.astype(float)


def get_balance(asset: str = "USDT") -> float:
    """Return free balance for the given asset."""
    balance = _exchange.fetch_balance()
    return float(balance["free"].get(asset, 0.0))


def place_market_order(symbol: str, side: str, amount: float) -> dict:
    """
    Place a market order.
    side: 'buy' | 'sell'
    amount: quantity in base currency (BTC for BTC/USDT)
    Returns the ccxt order dict.
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side: {side!r}. Must be 'buy' or 'sell'.")
    order = _exchange.create_market_order(symbol, side, amount)
    return order


def get_current_price(symbol: str = config.SYMBOL) -> float:
    """Fetch the latest ticker price."""
    ticker = _exchange.fetch_ticker(symbol)
    return float(ticker["last"])
