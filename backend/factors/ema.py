"""
EMA (Exponential Moving Average) Indicator

EMAs are trend-following indicators that give more weight to recent prices.
Multiple EMAs are used together to identify trend direction and strength.

Common periods:
    EMA(9): Very short-term trend
    EMA(20): Short-term trend
    EMA(50): Medium-term trend
    EMA(200): Long-term trend

Interpretation:
    Price > EMA: Bullish
    Price < EMA: Bearish
    EMA(short) > EMA(long): Uptrend
    EMA(short) < EMA(long): Downtrend
"""

from __future__ import annotations

from typing import Dict, Optional, List
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


def generate_ema_signal(
    price: float,
    ema9: float,
    ema20: float,
    ema50: float,
    ema200: float
) -> str:
    """
    Generate trading signal from EMA alignment

    Args:
        price: Current price
        ema9: 9-period EMA
        ema20: 20-period EMA
        ema50: 50-period EMA
        ema200: 200-period EMA

    Returns:
        Signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
    """
    # Check for NaN values
    values = [price, ema9, ema20, ema50, ema200]
    if any(pd.isna(v) for v in values):
        return "NEUTRAL"

    # Count bullish EMAs (price above EMA = bullish)
    bullish_count = sum([
        price > ema9,
        price > ema20,
        price > ema50,
        price > ema200
    ])

    # Check EMA alignment (shorter EMAs above longer EMAs = strong trend)
    perfect_bullish_alignment = (ema9 > ema20 > ema50 > ema200)
    perfect_bearish_alignment = (ema9 < ema20 < ema50 < ema200)

    # Generate signal
    if perfect_bullish_alignment and bullish_count >= 3:
        return "STRONG_BUY"  # Perfect bullish alignment
    elif bullish_count >= 3:
        return "BUY"  # Mostly bullish
    elif perfect_bearish_alignment and bullish_count <= 1:
        return "STRONG_SELL"  # Perfect bearish alignment
    elif bullish_count <= 1:
        return "SELL"  # Mostly bearish
    else:
        return "NEUTRAL"  # Mixed signals


def compute_ema(
    history: Dict[str, pd.DataFrame],
    top_spot: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Calculate EMA factor for all symbols

    Args:
        history: Historical price data by symbol
        top_spot: Optional spot data (unused)

    Returns:
        DataFrame with EMA values and signals
    """
    rows: List[dict] = []

    for symbol, df in history.items():
        # Require at least 200 candles for EMA(200)
        if df is None or df.empty or len(df) < 200:
            continue

        # Ensure proper date sorting
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['Date']):
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])

        df_sorted = df_copy.sort_values("Date", ascending=True).reset_index(drop=True)

        # Calculate EMAs
        ema9 = calculate_ema(df_sorted['Close'], 9)
        ema20 = calculate_ema(df_sorted['Close'], 20)
        ema50 = calculate_ema(df_sorted['Close'], 50)
        ema200 = calculate_ema(df_sorted['Close'], 200)

        # Get latest values
        latest_price = df_sorted['Close'].iloc[-1]
        latest_ema9 = ema9.iloc[-1] if not ema9.empty else np.nan
        latest_ema20 = ema20.iloc[-1] if not ema20.empty else np.nan
        latest_ema50 = ema50.iloc[-1] if not ema50.empty else np.nan
        latest_ema200 = ema200.iloc[-1] if not ema200.empty else np.nan

        if any(pd.isna(v) for v in [latest_ema9, latest_ema20, latest_ema50, latest_ema200]):
            continue

        # Generate signal
        signal = generate_ema_signal(
            latest_price, latest_ema9, latest_ema20, latest_ema50, latest_ema200
        )

        # Calculate trend strength (distance from EMA200)
        price_distance_pct = ((latest_price - latest_ema200) / latest_ema200) * 100
        strength = min(1.0, abs(price_distance_pct) / 10)  # Normalize to 0-1

        # Determine trend direction
        if latest_price > latest_ema200:
            trend = "UPTREND"
        elif latest_price < latest_ema200:
            trend = "DOWNTREND"
        else:
            trend = "NEUTRAL"

        rows.append({
            "Symbol": symbol,
            "EMA 9": float(latest_ema9),
            "EMA 20": float(latest_ema20),
            "EMA 50": float(latest_ema50),
            "EMA 200": float(latest_ema200),
            "Price vs EMA200": f"{price_distance_pct:+.2f}%",
            "Trend": trend,
            "EMA Signal": signal,
            "EMA Strength": float(strength)
        })

    # Sort by price distance from EMA200 (most bullish first)
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        # Extract numeric value from "Price vs EMA200" for sorting
        df_result['_sort_key'] = df_result['Price vs EMA200'].str.rstrip('%').astype(float)
        df_result = df_result.sort_values("_sort_key", ascending=False)
        df_result = df_result.drop(columns=['_sort_key'])

    return df_result


EMA_FACTOR = Factor(
    id="ema",
    name="EMA (9,20,50,200)",
    description="Exponential Moving Averages: Trend indicator. Price > EMAs = bullish, aligned EMAs = strong trend",
    columns=[
        {"key": "EMA 9", "label": "EMA 9", "type": "number", "sortable": True},
        {"key": "EMA 20", "label": "EMA 20", "type": "number", "sortable": True},
        {"key": "EMA 50", "label": "EMA 50", "type": "number", "sortable": True},
        {"key": "EMA 200", "label": "EMA 200", "type": "number", "sortable": True},
        {"key": "Price vs EMA200", "label": "Price vs EMA200", "type": "text", "sortable": True},
        {"key": "Trend", "label": "Trend", "type": "text", "sortable": True},
        {"key": "EMA Signal", "label": "Signal", "type": "text", "sortable": True},
        {"key": "EMA Strength", "label": "Strength", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_ema(history, top_spot),
)

MODULE_FACTORS = [EMA_FACTOR]
