"""
main.py – Entry point for the multi-pair trading bot with Rich terminal UI.

Layout:
  ┌─ Header ──────────────────────────────────────────┐
  ├─ Open Positions ──────────────────────────────────┤
  ├─ Trade History ───────────────────────────────────┤
  └─ Activity Log ────────────────────────────────────┘
"""

import time
import sys
from collections import deque
from datetime import datetime, timezone

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box as rich_box

import exchange
import strategy
import trader
import logger
import config


console = Console()
_log_lines: deque = deque(maxlen=18)
_ui_balance_usdt: float | None = None
_ui_top_pairs: list[str] = []
_ui_btc_filter: str = "UNKNOWN"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def _add_log(msg: str) -> None:
    _log_lines.append(f"[dim]{_now()}[/dim]  {msg}")


def _drain_trader_log() -> None:
    """Pull events written by trader.py into the UI log."""
    while trader.event_log:
        _add_log(trader.event_log.popleft())


# ── UI builders ───────────────────────────────────────────────────────────────

def _build_header() -> Panel:
    watchlist_count = len(config.WATCHLIST)
    top_pairs = _ui_top_pairs or config.WATCHLIST[:config.TOP_PAIRS_COUNT]
    pairs = "  [dim]|[/dim]  ".join(f"[cyan]{s}[/cyan]" for s in top_pairs)
    bal = "?" if _ui_balance_usdt is None else f"{_ui_balance_usdt:.2f} USDT"
    net   = "[bold green]TESTNET[/bold green]" if config.USE_TESTNET else "[bold red]LIVE[/bold red]"
    return Panel(
        f"[bold white]Crypto Trading Bot[/bold white]   "
        f"[yellow]{config.TIMEFRAME}[/yellow] (entry) / [yellow]{config.TREND_TIMEFRAME}[/yellow] (trend)   {net}   "
        f"[white]Balance:[/white] [bold]{bal}[/bold]   "
        f"[white]BTC Filter:[/white] [bold]{_ui_btc_filter}[/bold]   "
        f"[white]Top {len(top_pairs)}/{watchlist_count}:[/white] {pairs}   [dim]{_now()}[/dim]",
        box=rich_box.HORIZONTALS,
        padding=(0, 1),
    )


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
            _add_log(f"[yellow]RANK SKIP[/yellow] [cyan]{symbol}[/cyan]: {exc}")

    ranked.sort(key=lambda row: row["score"], reverse=True)
    top_pairs = [row["symbol"] for row in ranked[:config.TOP_PAIRS_COUNT]]
    return top_pairs, ranked


def _build_positions_panel() -> Panel:
    tbl = Table(box=rich_box.SIMPLE, expand=True, show_edge=False, padding=(0, 1))
    tbl.add_column("Symbol",         style="cyan",          min_width=10)
    tbl.add_column("Entry",          justify="right",       min_width=11)
    tbl.add_column("Current",        justify="right",       min_width=11)
    tbl.add_column("Side",           justify="center",      min_width=8)
    tbl.add_column("Qty",            justify="right",       min_width=9)
    tbl.add_column("Stop-Loss",      justify="right", style="red",   min_width=11)
    tbl.add_column("Take-Profit",    justify="right", style="green", min_width=11)
    tbl.add_column("Unrealised PnL", justify="right",       min_width=15)

    positions = trader.get_all_positions()
    if not positions:
        tbl.add_row("[dim]No open positions[/dim]", "", "", "", "", "", "", "")
    else:
        for symbol, pos in positions.items():
            try:
                current = exchange.get_current_price(symbol)
                side    = pos.get("side", "long")
                pnl     = round((current - pos["entry_price"]) * pos["qty"], 4) if side == "long" else round((pos["entry_price"] - current) * pos["qty"], 4)
                cur_str = f"{current:.2f}"
                pnl_str = f"[green]+{pnl:.4f}[/green]" if pnl >= 0 else f"[red]{pnl:.4f}[/red]"
            except Exception:
                side = "?"
                cur_str = "[red]?[/red]"
                pnl_str = "[red]?[/red]"
            tbl.add_row(
                symbol,
                f"{pos['entry_price']:.2f}",
                cur_str,
                side.upper(),
                str(pos["qty"]),
                f"{pos['stop_loss']:.2f}",
                f"{pos['take_profit']:.2f}",
                pnl_str,
            )

    return Panel(tbl, title="[bold]Open Positions[/bold]", box=rich_box.ROUNDED)


def _build_history_panel() -> Panel:
    tbl = Table(box=rich_box.SIMPLE, expand=True, show_edge=False, padding=(0, 1))
    tbl.add_column("Time",        style="dim",    min_width=19)
    tbl.add_column("Symbol",      style="cyan",   min_width=10)
    tbl.add_column("Side",        justify="center", min_width=12)
    tbl.add_column("Price",       justify="right", min_width=11)
    tbl.add_column("Qty",         justify="right", min_width=9)
    tbl.add_column("PnL (USDT)",  justify="right", min_width=13)

    trades = logger.get_history(limit=12)
    if not trades:
        tbl.add_row("[dim]No trades yet[/dim]", "", "", "", "", "")
    else:
        for t in trades:
            side = t["side"]
            if side == "OPEN_LONG":
                side_fmt = "[green]LONG OPEN[/green]"
            elif side == "OPEN_SHORT":
                side_fmt = "[red]SHORT OPEN[/red]"
            elif side == "CLOSE_TP":
                side_fmt = "[green]CLOSE TP ✓[/green]"
            elif side == "CLOSE_SL":
                side_fmt = "[red]CLOSE SL ✗[/red]"
            elif side == "CLOSE_REVERSAL":
                side_fmt = "[yellow]REVERSAL[/yellow]"
            else:
                side_fmt = f"[yellow]{side}[/yellow]"

            pnl = t.get("pnl_usdt")
            if pnl is None:
                pnl_str = "[dim]—[/dim]"
            elif pnl >= 0:
                pnl_str = f"[green]+{pnl:.4f}[/green]"
            else:
                pnl_str = f"[red]{pnl:.4f}[/red]"

            ts = t["timestamp"][:19].replace("T", " ")
            tbl.add_row(ts, t["symbol"], side_fmt, f"{t['price']:.2f}", str(t["qty"]), pnl_str)

    return Panel(tbl, title="[bold]Trade History[/bold]", box=rich_box.ROUNDED)


def _build_log_panel() -> Panel:
    body = "\n".join(_log_lines) if _log_lines else "[dim]Waiting for first candle close…[/dim]"
    return Panel(body, title="[bold]Activity Log[/bold]", box=rich_box.ROUNDED)


def _build_ui() -> Group:
    return Group(
        _build_header(),
        _build_positions_panel(),
        _build_history_panel(),
        _build_log_panel(),
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    global _ui_balance_usdt, _ui_top_pairs, _ui_btc_filter

    logger.init_db()
    logger.clear_history()
    last_candle_times: dict = {}
    selected_pairs: list[str] = list(config.WATCHLIST[:config.TOP_PAIRS_COUNT])
    last_rank_refresh = 0.0
    last_balance_refresh = 0.0
    btc_bullish = False

    _ui_top_pairs = selected_pairs

    _add_log(
        f"Bot started  —  watchlist: [cyan]{', '.join(config.WATCHLIST)}[/cyan]  "
        f"signal tf: [yellow]{config.TIMEFRAME}[/yellow]"
    )

    with Live(_build_ui(), console=console, refresh_per_second=2, screen=True) as live:
        while True:
            try:
                now_ts = time.time()

                if now_ts - last_rank_refresh >= config.RANKING_REFRESH_SECONDS:
                    selected_pairs, ranked = _rank_watchlist()
                    last_rank_refresh = now_ts
                    if selected_pairs:
                        _ui_top_pairs = selected_pairs
                        preview = ", ".join(selected_pairs)
                        _add_log(f"[white]Top pairs refreshed:[/white] [cyan]{preview}[/cyan]")
                    else:
                        _add_log("[yellow]Ranking returned no symbols; keeping previous top list[/yellow]")

                if now_ts - last_balance_refresh >= config.BALANCE_REFRESH_SECONDS:
                    try:
                        _ui_balance_usdt = exchange.get_balance("USDT")
                    except Exception as bal_exc:
                        _add_log(f"[yellow]Balance fetch failed:[/yellow] {bal_exc}")
                    last_balance_refresh = now_ts

                if config.ENABLE_BTC_MARKET_FILTER:
                    try:
                        btc_bullish = _is_btc_bullish()
                    except Exception as btc_exc:
                        btc_bullish = False
                        _add_log(f"[yellow]BTC filter fallback to bearish:[/yellow] {btc_exc}")
                else:
                    btc_bullish = True

                _ui_btc_filter = "BULLISH" if btc_bullish else "BEARISH"

                managed_symbols = sorted(set(selected_pairs) | set(trader.get_all_positions().keys()))
                for symbol in managed_symbols:
                    try:
                        df = _fetch_and_compute(symbol, config.TIMEFRAME)
                        htf_df = _fetch_and_compute(symbol, config.TREND_TIMEFRAME)

                        current_candle_time = df.index[-1]
                        new_candle = (current_candle_time != last_candle_times.get(symbol))

                        current_price = df.iloc[-1]["close"]
                        trader.check_exit_on_price(current_price, symbol)
                        _drain_trader_log()

                        if new_candle:
                            last_candle_times[symbol] = current_candle_time
                            sig = strategy.get_signal(df, htf_df)

                            if symbol not in selected_pairs:
                                sig = strategy.Signal.HOLD

                            if (
                                sig == strategy.Signal.BUY
                                and config.ENABLE_BTC_MARKET_FILTER
                                and not btc_bullish
                            ):
                                _add_log(
                                    f"[yellow]SKIP[/yellow] [cyan]{symbol}[/cyan]  "
                                    "BTC 4h trend is bearish"
                                )
                                sig = strategy.Signal.HOLD

                            atr_value = float(df.iloc[-1].get("atr", 0.0))
                            trader.execute(sig, current_price, symbol, atr_value)
                            _drain_trader_log()

                            sig_color = "green" if sig.value == "BUY" else "red" if sig.value == "SELL" else "dim"
                            _add_log(
                                f"[cyan]{symbol}[/cyan]  "
                                f"[{sig_color}]{sig.value}[/{sig_color}]  "
                                f"@ {current_price:.2f}"
                            )

                    except Exception as sym_exc:
                        _add_log(f"[red]ERROR [{symbol}]: {sym_exc}[/red]")

            except KeyboardInterrupt:
                break

            live.update(_build_ui())
            time.sleep(config.POLL_INTERVAL_SECONDS)

    console.print("\n[yellow]Bot stopped.[/yellow]")


if __name__ == "__main__":
    run()

