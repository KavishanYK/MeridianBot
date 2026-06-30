"""risk_manager.py – ATR-based position sizing and exit levels."""

import config


def calculate_position(balance_usdt: float, entry_price: float, atr: float, side: str = "long") -> dict:
    """
    Given available USDT balance and entry price, return:
      qty          – base quantity to buy (rounded to 5 decimal places)
    stop_loss    – stop loss level (1.5 x ATR, side-aware)
    tp1          – first target (1.5 x ATR, side-aware)
    tp2          – second target (3.0 x ATR, side-aware)
      trail_offset – trailing stop distance after TP1
      risk_amount  – USDT value being risked
    """
    if atr <= 0:
        return {
            "qty": 0.0,
            "stop_loss": entry_price,
            "tp1": entry_price,
            "tp2": entry_price,
            "trail_offset": 0.0,
            "risk_amount": 0.0,
        }

    if side not in ("long", "short"):
        raise ValueError("side must be 'long' or 'short'")

    risk_amount  = balance_usdt * config.RISK_PER_TRADE
    stop_distance = atr * config.ATR_STOP_MULTIPLIER
    qty          = round(risk_amount / stop_distance, 5)

    if side == "long":
        stop_loss = round(entry_price - stop_distance, 2)
        tp1 = round(entry_price + (atr * config.TP1_ATR_MULTIPLIER), 2)
        tp2 = round(entry_price + (atr * config.TP2_ATR_MULTIPLIER), 2)
    else:
        stop_loss = round(entry_price + stop_distance, 2)
        tp1 = round(entry_price - (atr * config.TP1_ATR_MULTIPLIER), 2)
        tp2 = round(entry_price - (atr * config.TP2_ATR_MULTIPLIER), 2)

    trail_offset = round(atr * config.TRAILING_ATR_MULTIPLIER, 2)

    return {
        "qty":         qty,
        "stop_loss":   stop_loss,
        "tp1":         tp1,
        "tp2":         tp2,
        "trail_offset": trail_offset,
        "risk_amount": round(risk_amount, 2),
    }


def should_stop_loss(current_price: float, stop_loss: float, side: str = "long") -> bool:
    if side == "long":
        return current_price <= stop_loss
    if side == "short":
        return current_price >= stop_loss
    raise ValueError("side must be 'long' or 'short'")


def should_take_profit(current_price: float, take_profit: float, side: str = "long") -> bool:
    if side == "long":
        return current_price >= take_profit
    if side == "short":
        return current_price <= take_profit
    raise ValueError("side must be 'long' or 'short'")
