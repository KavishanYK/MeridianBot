"""
strategy.py – EMA trend + ADX + volume + RSI pullback strategy.

Signals:
    BUY  – EMA trend up + ADX filter + volume confirmation + RSI pullback
                 + higher-timeframe trend up
    SELL – EMA trend down + ADX filter + volume confirmation + RSI pullback
                 + higher-timeframe trend down
    HOLD – everything else

All indicators are computed with plain pandas; no extra library needed.
"""

from enum import Enum
import pandas as pd
import config


class Signal(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ── Indicator helpers ──────────────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr_components = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    )
    tr = tr_components.max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_dm_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    plus_di = 100 * (plus_dm_smoothed / atr.replace(0, float("nan")))
    minus_di = 100 * (minus_dm_smoothed / atr.replace(0, float("nan")))

    di_sum = (plus_di + minus_di).replace(0, float("nan"))
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx


# ── Public API ────────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds EMA_fast, EMA_slow, RSI, ADX and volume_ma columns to a copy of `df`.
    Input df must have a 'close' column.
    """
    df = df.copy()
    df["ema_fast"] = _ema(df["close"], config.EMA_FAST)
    df["ema_slow"] = _ema(df["close"], config.EMA_SLOW)
    df["rsi"]      = _rsi(df["close"], config.RSI_PERIOD)
    df["adx"]      = _adx(df, config.ADX_PERIOD)
    df["volume_ma"] = df["volume"].rolling(config.VOLUME_MA_PERIOD).mean()
    return df


def min_required_candles() -> int:
    return max(
        config.EMA_SLOW * 3,
        config.RSI_PERIOD * 3,
        config.ADX_PERIOD * 3,
        config.VOLUME_MA_PERIOD * 3,
    )


def compute_strength_metrics(df: pd.DataFrame) -> dict | None:
    """
    Compute ranking metrics from the latest closed candle.

    score = ADX * 0.5 + VolumeStrength * 0.3 + TrendStrength * 0.2
    where:
      VolumeStrength = volume / volume_ma
      TrendStrength  = abs(ema_fast - ema_slow) / ema_slow * 100
    """
    if len(df) < min_required_candles():
        return None

    curr = df.iloc[-1]
    required = ["adx", "volume", "volume_ma", "ema_fast", "ema_slow"]
    if curr[required].isna().any() or curr["volume_ma"] <= 0 or curr["ema_slow"] == 0:
        return None

    adx = float(curr["adx"])
    volume_strength = float(curr["volume"] / curr["volume_ma"])
    trend_strength = float(abs(curr["ema_fast"] - curr["ema_slow"]) / abs(curr["ema_slow"]) * 100)
    score = (
        adx * config.SCORE_WEIGHT_ADX
        + volume_strength * config.SCORE_WEIGHT_VOLUME
        + trend_strength * config.SCORE_WEIGHT_TREND
    )

    return {
        "adx": adx,
        "volume_strength": volume_strength,
        "trend_strength": trend_strength,
        "score": score,
    }


def get_signal(df: pd.DataFrame, htf_df: pd.DataFrame) -> Signal:
    """
    Evaluate the latest closed candle and return BUY / SELL / HOLD.
    `df` and `htf_df` should already contain indicator columns
    (i.e. output of compute_indicators).
    """
    if len(df) < min_required_candles() or len(htf_df) < min_required_candles():
        return Signal.HOLD

    curr = df.iloc[-1]
    htf_curr = htf_df.iloc[-1]

    if curr[["ema_fast", "ema_slow", "rsi", "adx", "volume", "volume_ma"]].isna().any():
        return Signal.HOLD
    if htf_curr[["ema_fast", "ema_slow"]].isna().any():
        return Signal.HOLD

    ema_trend_up = curr["ema_fast"] > curr["ema_slow"]
    ema_trend_down = curr["ema_fast"] < curr["ema_slow"]
    htf_trend_up = htf_curr["ema_fast"] > htf_curr["ema_slow"]
    htf_trend_down = htf_curr["ema_fast"] < htf_curr["ema_slow"]

    adx_ok = curr["adx"] > config.ADX_MIN
    volume_ok = curr["volume"] > (curr["volume_ma"] * config.VOLUME_MIN_MULTIPLIER)
    rsi_pullback = config.RSI_PULLBACK_LOW <= curr["rsi"] <= config.RSI_PULLBACK_HIGH

    buy_signal = ema_trend_up and htf_trend_up and adx_ok and volume_ok and rsi_pullback
    sell_signal = ema_trend_down and htf_trend_down and adx_ok and volume_ok and rsi_pullback

    if buy_signal:
        return Signal.BUY
    if sell_signal:
        return Signal.SELL
    return Signal.HOLD
