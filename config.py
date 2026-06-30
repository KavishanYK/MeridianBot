# ─── Trading Bot Configuration ──────────────────────────────────────────────────

# Exchange
USE_TESTNET = True                   # Flip to False for live trading
EXCHANGE_MARKET_TYPE = "futures"     # "spot" or "futures"
ENABLE_SHORT_ENTRIES = True          # Requires futures mode and futures-enabled API keys
ENABLE_SIGNAL_REVERSAL = True        # Close/reverse on opposite signal

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
RANKING_TIMEFRAME = "5m"            # Faster ranking response to current momentum
RANKING_REFRESH_SECONDS = 900        # Re-rank every 15 minutes
TOP_PAIRS_COUNT = len(WATCHLIST)     # Trade all symbols in the watchlist
SCORE_WEIGHT_ADX = 0.5
SCORE_WEIGHT_VOLUME = 0.3
SCORE_WEIGHT_TREND = 0.2

# Market regime filter (crypto beta control)
BTC_FILTER_SYMBOL = "BTC/USDT"
BTC_FILTER_TIMEFRAME = "4h"
ENABLE_BTC_MARKET_FILTER = False     # Disabled to avoid blocking long entries

# UI refresh helpers
BALANCE_REFRESH_SECONDS = 30

# Strategy – EMA trend + ADX + volume + RSI pullback
EMA_FAST    = 9
EMA_SLOW    = 21
RSI_PERIOD  = 14
RSI_LONG_LOW  = 35
RSI_LONG_HIGH = 65
RSI_SHORT_LOW = 35
RSI_SHORT_HIGH = 65
ADX_PERIOD   = 14
ADX_MIN      = 15                    # Lower threshold to allow weaker trends
ADX_STRONG   = 35
VOLUME_MA_PERIOD   = 20
VOLUME_MIN_MULTIPLIER = 0.85         # Accept slightly below-MA volume setups
ATR_PERIOD = 14

# Session filter (UTC): 08:00-12:00 and 13:00-17:00
ENABLE_SESSION_FILTER = False
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
