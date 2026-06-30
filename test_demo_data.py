import importlib
import unittest

import config
import risk_manager
import strategy
import trader


def _build_ohlcv(n: int = 120):
    import pandas as pd

    idx = pd.date_range("2026-01-01", periods=n, freq="3min")
    rows = []
    base = 100.0
    for i in range(n):
        close = base + i * 0.2
        high = close + 0.5
        low = close - 0.5
        open_ = close - 0.1
        volume = 100 + (i % 20)
        rows.append((open_, high, low, close, volume))

    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close", "volume"])


class DemoDataTests(unittest.TestCase):
    def setUp(self):
        # Keep tests deterministic and independent from UTC session windows.
        self._session_flag = config.ENABLE_SESSION_FILTER
        config.ENABLE_SESSION_FILTER = False

    def tearDown(self):
        config.ENABLE_SESSION_FILTER = self._session_flag

    def test_strategy_buy_signal_on_demo_data(self):
        entry_df = strategy.compute_indicators(_build_ohlcv())
        htf_df = strategy.compute_indicators(_build_ohlcv())

        # Force a valid long-continuation setup on the latest candles.
        prev_i = entry_df.index[-2]
        curr_i = entry_df.index[-1]
        entry_df.loc[prev_i, "ema_fast"] = 120.0
        entry_df.loc[prev_i, "ema_slow"] = 118.0
        entry_df.loc[prev_i, "low"] = 119.0

        entry_df.loc[curr_i, "ema_fast"] = 121.0
        entry_df.loc[curr_i, "ema_slow"] = 119.0
        entry_df.loc[curr_i, "close"] = 122.0
        entry_df.loc[curr_i, "adx"] = 25.0
        entry_df.loc[curr_i, "plus_di"] = 30.0
        entry_df.loc[curr_i, "minus_di"] = 10.0
        entry_df.loc[curr_i, "rsi"] = 50.0
        entry_df.loc[curr_i, "volume"] = 200.0
        entry_df.loc[curr_i, "volume_ma"] = 100.0
        entry_df.loc[curr_i, "atr"] = 1.2

        htf_df.loc[htf_df.index[-1], "ema_fast"] = 220.0
        htf_df.loc[htf_df.index[-1], "ema_slow"] = 210.0

        sig = strategy.get_signal(entry_df, htf_df)
        self.assertEqual(sig, strategy.Signal.BUY)

    def test_risk_manager_atr_position_sizing(self):
        sizing = risk_manager.calculate_position(balance_usdt=1000.0, entry_price=100.0, atr=2.0)
        # risk=10, stop_distance=3 => qty=3.33333
        self.assertAlmostEqual(sizing["qty"], 3.33333, places=5)
        self.assertEqual(sizing["stop_loss"], 97.0)
        self.assertEqual(sizing["tp1"], 103.0)
        self.assertEqual(sizing["tp2"], 106.0)

    def test_trader_buy_then_tp1_tp2_flow(self):
        # Reload to reset module globals between tests.
        t = importlib.reload(trader)

        captured_trades = []

        def fake_balance(_asset="USDT"):
            return 1000.0

        def fake_order(_symbol, _side, _amount):
            return {"id": "demo-order"}

        def fake_log_trade(**kwargs):
            captured_trades.append(kwargs)

        t.exchange.get_balance = fake_balance
        t.exchange.place_market_order = fake_order
        t.logger.log_trade = fake_log_trade

        t.execute(strategy.Signal.BUY, current_price=100.0, symbol="BTC/USDT", atr=2.0)
        self.assertTrue(t.has_position("BTC/USDT"))

        # Hit TP1 for partial close.
        t.check_exit_on_price(103.0, "BTC/USDT")
        pos = t.get_position("BTC/USDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos["tp1_hit"])
        self.assertGreater(pos["remaining_qty"], 0)

        # Hit TP2 for full close.
        t.check_exit_on_price(106.0, "BTC/USDT")
        self.assertFalse(t.has_position("BTC/USDT"))

        sides = [x["side"] for x in captured_trades]
        self.assertIn("BUY", sides)
        self.assertIn("CLOSE_TP1", sides)
        self.assertIn("CLOSE_TP2", sides)


if __name__ == "__main__":
    unittest.main(verbosity=2)
