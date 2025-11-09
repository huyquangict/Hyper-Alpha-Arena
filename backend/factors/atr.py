"""
ATR (Average True Range) Indicator

ATR is a volatility indicator that measures the average range of price movement.
It's used for risk management and position sizing, not for directional signals.

Formula:
    True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
    ATR = EMA(True Range, period)

Interpretation:
    High ATR: High volatility → Wider stops, smaller positions
    Low ATR: Low volatility → Tighter stops, larger positions
    Rising ATR: Increasing volatility
    Falling ATR: Decreasing volatility
"""

from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def calculate_true_range(df: pd.DataFrame) -> pd.Series:
    """
    Calculate True Range

    Args:
        df: DataFrame with 'High', 'Low', 'Close' columns

    Returns:
        True Range series
    """
    if len(df) < 2:
        return pd.Series([np.nan] * len(df), index=df.index)

    # Calculate components of true range
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()

    # True Range is the maximum of the three
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    return true_range


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range

    Args:
        df: DataFrame with OHLC data
        period: ATR period (default 14)

    Returns:
        ATR series
    """
    if len(df) < period + 1:
        return pd.Series([np.nan] * len(df), index=df.index)

    # Calculate True Range
    true_range = calculate_true_range(df)

    # Calculate ATR using Wilder's smoothing (EMA)
    atr = true_range.ewm(span=period, adjust=False).mean()

    return atr


def calculate_atr_percent(atr: float, price: float) -> float:
    """
    Calculate ATR as percentage of price

    Args:
        atr: ATR value
        price: Current price

    Returns:
        ATR as percentage
    """
    if pd.isna(atr) or pd.isna(price) or price == 0:
        return 0.0

    return (atr / price) * 100


def generate_atr_signal(atr_pct: float, atr_change_pct: float = None) -> str:
    """
    Generate volatility assessment from ATR

    Args:
        atr_pct: ATR as percentage of price
        atr_change_pct: Change in ATR (for trend detection)

    Returns:
        Volatility state: "VERY_HIGH" | "HIGH" | "NORMAL" | "LOW" | "VERY_LOW"
    """
    if pd.isna(atr_pct):
        return "NORMAL"

    # Classify volatility levels for crypto
    # Crypto typically has higher volatility than traditional assets
    if atr_pct > 10:
        return "VERY_HIGH"  # Extreme volatility
    elif atr_pct > 5:
        return "HIGH"  # High volatility
    elif atr_pct > 2:
        return "NORMAL"  # Normal volatility
    elif atr_pct > 1:
        return "LOW"  # Low volatility
    else:
        return "VERY_LOW"  # Very low volatility


def compute_atr(
    history: Dict[str, pd.DataFrame],
    top_spot: Optional[pd.DataFrame] = None,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate ATR factor for all symbols

    Args:
        history: Historical price data by symbol
        top_spot: Optional spot data (unused)
        period: ATR period (default 14)

    Returns:
        DataFrame with ATR values and volatility assessment
    """
    rows: List[dict] = []

    for symbol, df in history.items():
        if df is None or df.empty or len(df) < period + 1:
            continue

        # Ensure proper date sorting
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['Date']):
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])

        df_sorted = df_copy.sort_values("Date", ascending=True).reset_index(drop=True)

        # Calculate ATR
        atr_series = calculate_atr(df_sorted, period)

        # Get latest values
        latest_atr = atr_series.iloc[-1] if not atr_series.empty else np.nan
        latest_price = df_sorted['Close'].iloc[-1]

        if pd.isna(latest_atr):
            continue

        # Calculate ATR as percentage of price
        atr_pct = calculate_atr_percent(latest_atr, latest_price)

        # Calculate ATR change (volatility trend)
        if len(atr_series) >= 2:
            prev_atr = atr_series.iloc[-2]
            atr_change_pct = ((latest_atr - prev_atr) / prev_atr) * 100 if prev_atr > 0 else 0
        else:
            atr_change_pct = 0

        # Generate volatility signal
        volatility_state = generate_atr_signal(atr_pct, atr_change_pct)

        # Determine volatility trend
        if atr_change_pct > 10:
            trend = "RISING"
        elif atr_change_pct < -10:
            trend = "FALLING"
        else:
            trend = "STABLE"

        # Suggested position size multiplier based on volatility
        # Lower volatility = larger positions, higher volatility = smaller positions
        if atr_pct > 10:
            position_multiplier = 0.5  # 50% of normal position
        elif atr_pct > 5:
            position_multiplier = 0.75  # 75% of normal position
        elif atr_pct > 2:
            position_multiplier = 1.0  # Normal position
        else:
            position_multiplier = 1.25  # 125% of normal position

        rows.append({
            "Symbol": symbol,
            "ATR": float(latest_atr),
            "ATR %": float(atr_pct),
            "ATR Change %": float(atr_change_pct),
            "Volatility": volatility_state,
            "Vol Trend": trend,
            "Position Multiplier": float(position_multiplier)
        })

    # Sort by ATR percentage (most volatile first)
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        df_result = df_result.sort_values("ATR %", ascending=False)

    return df_result


ATR_FACTOR = Factor(
    id="atr",
    name="ATR (14)",
    description="Average True Range: Volatility indicator. Higher ATR = higher volatility = wider stops needed",
    columns=[
        {"key": "ATR", "label": "ATR", "type": "number", "sortable": True},
        {"key": "ATR %", "label": "ATR %", "type": "number", "sortable": True},
        {"key": "ATR Change %", "label": "ATR Change %", "type": "number", "sortable": True},
        {"key": "Volatility", "label": "Volatility", "type": "text", "sortable": True},
        {"key": "Vol Trend", "label": "Vol Trend", "type": "text", "sortable": True},
        {"key": "Position Multiplier", "label": "Position Multiplier", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_atr(history, top_spot, 14),
)

MODULE_FACTORS = [ATR_FACTOR]
