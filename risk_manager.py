"""
risk_manager.py – Position sizing and SL/TP calculation.
"""

import config


def calculate_position(balance_usdt: float, entry_price: float) -> dict:
    """
    Given available USDT balance and entry price, return:
      qty          – amount of BTC to buy (rounded to 5 decimal places)
      stop_loss    – price at which to cut the loss
      take_profit  – price at which to take profit
      risk_amount  – USDT value being risked
    """
    risk_amount  = balance_usdt * config.RISK_PER_TRADE
    qty          = round(risk_amount / entry_price, 5)
    stop_loss    = round(entry_price * (1 - config.STOP_LOSS_PCT), 2)
    take_profit  = round(entry_price * (1 + config.TAKE_PROFIT_PCT), 2)

    return {
        "qty":         qty,
        "stop_loss":   stop_loss,
        "take_profit": take_profit,
        "risk_amount": round(risk_amount, 2),
    }


def should_stop_loss(current_price: float, stop_loss: float) -> bool:
    return current_price <= stop_loss


def should_take_profit(current_price: float, take_profit: float) -> bool:
    return current_price >= take_profit
