"""
RSI (Relative Strength Index) Indicator

The RSI is a momentum oscillator that measures the speed and magnitude of
recent price changes to evaluate overbought or oversold conditions.

Formula:
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss

Interpretation:
    RSI > 70: Overbought (potential SELL signal)
    RSI < 30: Oversold (potential BUY signal)
    50: Neutral zone
"""

from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate RSI for a price series

    Args:
        df: DataFrame with 'Close' column
        period: RSI period (default 14)

    Returns:
        Series of RSI values
    """
    if len(df) < period + 1:
        return pd.Series([np.nan] * len(df), index=df.index)

    # Calculate price changes
    delta = df['Close'].diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate average gain and loss using Wilder's smoothing method
    # First average
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Smoothed averages (Wilder's method)
    for i in range(period, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def generate_rsi_signal(rsi_value: float) -> str:
    """
    Generate trading signal from RSI value

    Args:
        rsi_value: RSI value (0-100)

    Returns:
        Signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
    """
    if pd.isna(rsi_value):
        return "NEUTRAL"

    if rsi_value < 20:
        return "STRONG_BUY"  # Severely oversold
    elif rsi_value < 30:
        return "BUY"  # Oversold
    elif rsi_value > 80:
        return "STRONG_SELL"  # Severely overbought
    elif rsi_value > 70:
        return "SELL"  # Overbought
    else:
        return "NEUTRAL"


def compute_rsi(
    history: Dict[str, pd.DataFrame],
    top_spot: Optional[pd.DataFrame] = None,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate RSI factor for all symbols

    Args:
        history: Historical price data by symbol
        top_spot: Optional spot data (unused)
        period: RSI period (default 14)

    Returns:
        DataFrame with RSI values and signals
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

        # Calculate RSI
        rsi_series = calculate_rsi(df_sorted, period)

        # Get latest RSI value
        latest_rsi = rsi_series.iloc[-1] if not rsi_series.empty else np.nan

        if pd.isna(latest_rsi):
            continue

        # Generate signal
        signal = generate_rsi_signal(latest_rsi)

        # Calculate signal strength (distance from neutral zone)
        if latest_rsi < 50:
            # Oversold side: more oversold = stronger buy signal
            strength = max(0, (50 - latest_rsi) / 50)  # 0 to 1
        else:
            # Overbought side: more overbought = stronger sell signal
            strength = max(0, (latest_rsi - 50) / 50)  # 0 to 1

        rows.append({
            "Symbol": symbol,
            "RSI": float(latest_rsi),
            "RSI Signal": signal,
            "RSI Strength": float(strength)
        })

    # Sort by RSI (ascending - most oversold first)
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        df_result = df_result.sort_values("RSI", ascending=True)

    return df_result


RSI_FACTOR = Factor(
    id="rsi",
    name="RSI (14)",
    description="Relative Strength Index: Momentum oscillator (0-100). <30=oversold (BUY), >70=overbought (SELL)",
    columns=[
        {"key": "RSI", "label": "RSI", "type": "number", "sortable": True},
        {"key": "RSI Signal", "label": "Signal", "type": "text", "sortable": True},
        {"key": "RSI Strength", "label": "Strength", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_rsi(history, top_spot, period=14),
)

MODULE_FACTORS = [RSI_FACTOR]
