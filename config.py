# ─── Trading Bot Configuration ──────────────────────────────────────────────────

# Exchange
USE_TESTNET = True                   # Flip to False for live trading

# Market
WATCHLIST   = [
	"BTC/USDT", "ETH/USDT", "SOL/USDT",
]
SYMBOLS     = WATCHLIST              # Backward-compatible alias
SYMBOL      = WATCHLIST[0]           # Default / fallback symbol
TIMEFRAME   = "3m"                   # Entry timeframe (1m/3m/5m/10m)
TREND_TIMEFRAME = "15m"              # Higher timeframe for trend direction
HTF_TIMEFRAME = TREND_TIMEFRAME       # Backward-compatible alias
CANDLES     = 220                    # How many candles to fetch per cycle

# Portfolio rotation
RANKING_TIMEFRAME = "15m"           # Timeframe used for ranking candidates
RANKING_REFRESH_SECONDS = 3600       # Re-rank watchlist every hour
TOP_PAIRS_COUNT = 3                  # Trade only top N symbols
SCORE_WEIGHT_ADX = 0.5
SCORE_WEIGHT_VOLUME = 0.3
SCORE_WEIGHT_TREND = 0.2

# Market regime filter (crypto beta control)
BTC_FILTER_SYMBOL = "BTC/USDT"
BTC_FILTER_TIMEFRAME = "4h"
ENABLE_BTC_MARKET_FILTER = True

# UI refresh helpers
BALANCE_REFRESH_SECONDS = 30

# Strategy – EMA trend + ADX + volume + RSI pullback
EMA_FAST    = 9
EMA_SLOW    = 21
RSI_PERIOD  = 14
RSI_LONG_LOW  = 40
RSI_LONG_HIGH = 55
RSI_SHORT_LOW = 45
RSI_SHORT_HIGH = 60
ADX_PERIOD   = 14
ADX_MIN      = 20                    # Trend-strength filter for scalping
ADX_STRONG   = 35
VOLUME_MA_PERIOD   = 20
VOLUME_MIN_MULTIPLIER = 1.0
ATR_PERIOD = 14

# Session filter (UTC): 08:00-12:00 and 13:00-17:00
ENABLE_SESSION_FILTER = True
ALLOWED_UTC_WINDOWS = [(8, 12), (13, 17)]

# Risk management (as fractions of available balance)
RISK_PER_TRADE  = 0.01               # Risk 1% of account per trade
ATR_STOP_MULTIPLIER = 1.5
TP1_ATR_MULTIPLIER = 1.5
TP2_ATR_MULTIPLIER = 3.0
TRAILING_ATR_MULTIPLIER = 1.0

# Circuit breakers
DAILY_LOSS_LIMIT_PCT = 0.02          # Stop new entries after -2% daily realized PnL
MAX_CONSECUTIVE_LOSSES = 3
CONSECUTIVE_LOSS_PAUSE_SECONDS = 3600
MAX_OPEN_POSITIONS = 1

# Polling
POLL_INTERVAL_SECONDS = 15           # Faster loop for lower-timeframe entries

# Logging
DB_PATH = "trades.db"
