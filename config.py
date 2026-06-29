# ─── Trading Bot Configuration ──────────────────────────────────────────────────

# Exchange
USE_TESTNET = True                   # Flip to False for live trading

# Market
WATCHLIST   = [
	"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
	"LINK/USDT", "AVAX/USDT", "ADA/USDT", "SUI/USDT", "HBAR/USDT", "DOGE/USDT",
]
SYMBOLS     = WATCHLIST              # Backward-compatible alias
SYMBOL      = WATCHLIST[0]           # Default / fallback symbol
TIMEFRAME   = "15m"                  # Signal timeframe
HTF_TIMEFRAME = "4h"                 # Higher-timeframe trend filter
CANDLES     = 100                    # How many candles to fetch per cycle

# Portfolio rotation
RANKING_TIMEFRAME = "1h"            # Timeframe used for ranking candidates
RANKING_REFRESH_SECONDS = 3600       # Re-rank watchlist every hour
TOP_PAIRS_COUNT = 5                  # Trade only top N symbols
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
RSI_PULLBACK_LOW  = 40
RSI_PULLBACK_HIGH = 60
ADX_PERIOD   = 14
ADX_MIN      = 25                    # Trend-strength filter
ADX_STRONG   = 35
VOLUME_MA_PERIOD   = 20
VOLUME_MIN_MULTIPLIER = 1.2

# Risk management (as fractions of available balance)
RISK_PER_TRADE  = 0.10               # Max 10% of USDT balance per trade
STOP_LOSS_PCT   = 0.02               # 2% stop-loss below entry
TAKE_PROFIT_PCT = 0.04               # 4% take-profit above entry

# Polling
POLL_INTERVAL_SECONDS = 60           # How often to check if a new candle closed

# Logging
DB_PATH = "trades.db"
