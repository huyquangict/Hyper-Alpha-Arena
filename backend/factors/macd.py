"""
MACD (Moving Average Convergence Divergence) Indicator

MACD is a trend-following momentum indicator that shows the relationship
between two moving averages of a security's price.

Formula:
    MACD Line = EMA(12) - EMA(26)
    Signal Line = EMA(9) of MACD Line
    Histogram = MACD Line - Signal Line

Interpretation:
    MACD > Signal: Bullish (BUY signal)
    MACD < Signal: Bearish (SELL signal)
    Histogram > 0: Bullish momentum
    Histogram < 0: Bearish momentum
    Crossovers: Strong trend change signals
"""

from __future__ import annotations

from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np

from models import Factor


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average

    Args:
        series: Price series
        period: EMA period

    Returns:
        EMA series
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD, Signal Line, and Histogram

    Args:
        df: DataFrame with 'Close' column
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line EMA period (default 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    if len(df) < slow_period:
        nan_series = pd.Series([np.nan] * len(df), index=df.index)
        return nan_series, nan_series, nan_series

    # Calculate EMAs
    ema_fast = calculate_ema(df['Close'], fast_period)
    ema_slow = calculate_ema(df['Close'], slow_period)

    # MACD Line
    macd_line = ema_fast - ema_slow

    # Signal Line (EMA of MACD)
    signal_line = calculate_ema(macd_line, signal_period)

    # Histogram
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def generate_macd_signal(
    macd: float,
    signal: float,
    histogram: float,
    prev_histogram: float = None
) -> str:
    """
    Generate trading signal from MACD values

    Args:
        macd: Current MACD value
        signal: Current signal line value
        histogram: Current histogram value
        prev_histogram: Previous histogram value (for crossover detection)

    Returns:
        Signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
    """
    if pd.isna(macd) or pd.isna(signal) or pd.isna(histogram):
        return "NEUTRAL"

    # Check for crossover
    is_bullish_crossover = False
    is_bearish_crossover = False

    if prev_histogram is not None and not pd.isna(prev_histogram):
        # Bullish crossover: histogram crosses from negative to positive
        if prev_histogram < 0 and histogram > 0:
            is_bullish_crossover = True
        # Bearish crossover: histogram crosses from positive to negative
        elif prev_histogram > 0 and histogram < 0:
            is_bearish_crossover = True

    # Generate signal
    if is_bullish_crossover:
        return "STRONG_BUY"  # Bullish crossover
    elif is_bearish_crossover:
        return "STRONG_SELL"  # Bearish crossover
    elif histogram > 0:
        if macd > 0:
            return "BUY"  # Bullish: MACD > signal and both positive
        else:
            return "NEUTRAL"  # Bullish but weak
    elif histogram < 0:
        if macd < 0:
            return "SELL"  # Bearish: MACD < signal and both negative
        else:
            return "NEUTRAL"  # Bearish but weak
    else:
        return "NEUTRAL"


def compute_macd(
    history: Dict[str, pd.DataFrame],
    top_spot: Optional[pd.DataFrame] = None,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Calculate MACD factor for all symbols

    Args:
        history: Historical price data by symbol
        top_spot: Optional spot data (unused)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)

    Returns:
        DataFrame with MACD values and signals
    """
    rows: List[dict] = []

    for symbol, df in history.items():
        if df is None or df.empty or len(df) < slow_period + signal_period:
            continue

        # Ensure proper date sorting
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['Date']):
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])

        df_sorted = df_copy.sort_values("Date", ascending=True).reset_index(drop=True)

        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(
            df_sorted, fast_period, slow_period, signal_period
        )

        # Get latest values
        latest_macd = macd_line.iloc[-1] if not macd_line.empty else np.nan
        latest_signal = signal_line.iloc[-1] if not signal_line.empty else np.nan
        latest_histogram = histogram.iloc[-1] if not histogram.empty else np.nan
        prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else None

        if pd.isna(latest_macd) or pd.isna(latest_signal):
            continue

        # Generate signal
        signal_str = generate_macd_signal(
            latest_macd, latest_signal, latest_histogram, prev_histogram
        )

        # Calculate signal strength (normalized histogram magnitude)
        # Strength based on histogram distance from zero
        strength = min(1.0, abs(latest_histogram) / (abs(latest_macd) + 1e-6))

        rows.append({
            "Symbol": symbol,
            "MACD": float(latest_macd),
            "MACD Signal": float(latest_signal),
            "MACD Histogram": float(latest_histogram),
            "MACD Direction": signal_str,
            "MACD Strength": float(strength)
        })

    # Sort by histogram (most bullish first)
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        df_result = df_result.sort_values("MACD Histogram", ascending=False)

    return df_result


MACD_FACTOR = Factor(
    id="macd",
    name="MACD (12,26,9)",
    description="Moving Average Convergence Divergence: Trend indicator. Histogram > 0 = bullish, < 0 = bearish",
    columns=[
        {"key": "MACD", "label": "MACD", "type": "number", "sortable": True},
        {"key": "MACD Signal", "label": "Signal Line", "type": "number", "sortable": True},
        {"key": "MACD Histogram", "label": "Histogram", "type": "number", "sortable": True},
        {"key": "MACD Direction", "label": "Direction", "type": "text", "sortable": True},
        {"key": "MACD Strength", "label": "Strength", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_macd(history, top_spot, 12, 26, 9),
)

MODULE_FACTORS = [MACD_FACTOR]
