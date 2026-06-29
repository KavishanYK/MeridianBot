# Crypto Trading Bot

A rule-based cryptocurrency trading bot for Binance (Testnet / Live) using an **EMA trend + ADX + volume + RSI pullback** strategy with **higher-timeframe confirmation**, **hourly watchlist ranking**, and a **BTC market regime filter**.

## Strategy

| Condition | Signal |
|---|---|
| Signal timeframe trend: EMA9 > EMA21, HTF trend: EMA9 > EMA21, ADX > 25, RSI between 40-60, volume > volume MA(20) x 1.2 | **BUY** |
| Signal timeframe trend: EMA9 < EMA21, HTF trend: EMA9 < EMA21, ADX > 25, RSI between 40-60, volume > volume MA(20) x 1.2 | **SELL** |
| Anything else | **HOLD** |

### Portfolio Selection Layer

Every hour, the bot ranks symbols in `WATCHLIST` and trades only the top `TOP_PAIRS_COUNT` symbols.

Scoring formula:

```
score = ADX * 0.5 + VolumeStrength * 0.3 + TrendStrength * 0.2
```

where:
- `VolumeStrength = volume / volume_ma`
- `TrendStrength = abs(ema_fast - ema_slow) / ema_slow * 100`

Before opening new longs, the bot checks BTC regime:
- `BTC_FILTER_SYMBOL` on `BTC_FILTER_TIMEFRAME`
- allows long entries only when `btc_ema_fast > btc_ema_slow`

Exits are managed automatically via **Stop-Loss (2%)** and **Take-Profit (4%)**, checked every poll interval.

## Project Structure

```
crypto_bot/
├── config.py          # All tunable parameters
├── exchange.py        # Binance/ccxt wrapper (OHLCV, balance, orders)
├── strategy.py        # EMA + RSI indicators and signal logic
├── risk_manager.py    # Position sizing, SL/TP calculation
├── trader.py          # Order execution and position state
├── logger.py          # SQLite trade journal (trades.db)
├── main.py            # Main loop
├── requirements.txt
├── .env.example       # API key template
└── .gitignore
```

## Setup

### 1. Clone / create the project directory

```bash
cd crypto_bot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> **Testnet keys:** Create them at https://testnet.binance.vision  
> **Live keys:** Create them at https://www.binance.com/en/my/settings/api-management

### 5. Configure the bot (optional)

Edit `config.py` to adjust:

| Parameter | Default | Description |
|---|---|---|
| `USE_TESTNET` | `True` | Flip to `False` for live trading |
| `SYMBOL` | `BTC/USDT` | Trading pair |
| `TIMEFRAME` | `15m` | Signal timeframe |
| `HTF_TIMEFRAME` | `4h` | Higher-timeframe trend confirmation |
| `WATCHLIST` | 11 symbols | Universe considered for hourly ranking |
| `RANKING_TIMEFRAME` | `1h` | Timeframe used to score watchlist symbols |
| `RANKING_REFRESH_SECONDS` | `3600` | Re-ranking interval |
| `TOP_PAIRS_COUNT` | `5` | Trade only this many strongest symbols |
| `SCORE_WEIGHT_ADX` | `0.5` | ADX weight in ranking score |
| `SCORE_WEIGHT_VOLUME` | `0.3` | Volume strength weight in ranking score |
| `SCORE_WEIGHT_TREND` | `0.2` | Trend strength weight in ranking score |
| `ENABLE_BTC_MARKET_FILTER` | `True` | Gate long entries by BTC trend |
| `BTC_FILTER_SYMBOL` | `BTC/USDT` | Symbol used for regime filter |
| `BTC_FILTER_TIMEFRAME` | `4h` | Timeframe used for BTC trend filter |
| `EMA_FAST` | `9` | Fast EMA period |
| `EMA_SLOW` | `21` | Slow EMA period |
| `RSI_PERIOD` | `14` | RSI period |
| `RSI_PULLBACK_LOW` | `40` | Lower bound for RSI pullback entries |
| `RSI_PULLBACK_HIGH` | `60` | Upper bound for RSI pullback entries |
| `ADX_PERIOD` | `14` | ADX period |
| `ADX_MIN` | `25` | Minimum trend strength for entries |
| `VOLUME_MA_PERIOD` | `20` | Rolling volume moving average period |
| `VOLUME_MIN_MULTIPLIER` | `1.2` | Volume must exceed MA by this multiplier |
| `RISK_PER_TRADE` | `0.10` | Fraction of balance per trade (10%) |
| `STOP_LOSS_PCT` | `0.02` | Stop-loss distance from entry (2%) |
| `TAKE_PROFIT_PCT` | `0.04` | Take-profit distance from entry (4%) |
| `POLL_INTERVAL_SECONDS` | `60` | How often to poll for new candle |

## Running the Bot

```bash
source venv/bin/activate
python main.py
```

The bot prints a status line on every new candle close:

```
────────────────────────────────────────────────────────────
[2025-01-15 10:00:00 UTC]  Signal: BUY
  Price : 43210.50
  EMA9  : 43150.22  |  EMA21: 43050.10
  RSI14 : 54.32
  Position: FLAT
────────────────────────────────────────────────────────────
[trader] BUY  0.00046 BTC @ 43210.50  SL=42346.29  TP=44938.92
```

Stop with **Ctrl+C**.

## Trade History

All trades are logged to `trades.db` (SQLite). Query it directly:

```bash
sqlite3 trades.db "SELECT * FROM trades ORDER BY id DESC LIMIT 10;"
```

Or in Python:

```python
import logger
for trade in logger.get_history(limit=20):
    print(trade)
```

## Safety Notes

- **Always test on Testnet first.** Set `USE_TESTNET = True` (default).
- The bot holds at most **one position** at a time.
- Ensure your Binance API key has **Spot trading enabled** and **withdrawals disabled**.
- Never commit your `.env` file — it is already in `.gitignore`.

## Disclaimer

This bot is for educational purposes only. Cryptocurrency trading carries significant financial risk. Past performance does not guarantee future results.
