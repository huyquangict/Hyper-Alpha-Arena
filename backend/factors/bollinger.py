"""
Bollinger Bands Indicator

Bollinger Bands consist of a middle band (SMA) with an upper and lower band
at a specified number of standard deviations away.

Formula:
    Middle Band = SMA(20)
    Upper Band = SMA(20) + (2 × StdDev)
    Lower Band = SMA(20) - (2 × StdDev)

Interpretation:
    Price < Lower Band: Oversold (potential BUY)
    Price > Upper Band: Overbought (potential SELL)
    Price near Middle Band: Neutral
    Band Width: Volatility indicator
"""

from __future__ import annotations

from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np

from models import Factor


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands

    Args:
        df: DataFrame with 'Close' column
        period: SMA period (default 20)
        std_dev: Number of standard deviations (default 2.0)

    Returns:
        Tuple of (middle_band, upper_band, lower_band, bandwidth)
    """
    if len(df) < period:
        nan_series = pd.Series([np.nan] * len(df), index=df.index)
        return nan_series, nan_series, nan_series, nan_series

    # Calculate middle band (SMA)
    middle_band = df['Close'].rolling(window=period).mean()

    # Calculate standard deviation
    rolling_std = df['Close'].rolling(window=period).std()

    # Calculate upper and lower bands
    upper_band = middle_band + (std_dev * rolling_std)
    lower_band = middle_band - (std_dev * rolling_std)

    # Calculate bandwidth (volatility measure)
    bandwidth = (upper_band - lower_band) / middle_band * 100

    return middle_band, upper_band, lower_band, bandwidth


def calculate_bb_position(price: float, lower: float, middle: float, upper: float) -> float:
    """
    Calculate price position within Bollinger Bands

    Args:
        price: Current price
        lower: Lower band value
        middle: Middle band value
        upper: Upper band value

    Returns:
        Position: -1 to +1 (-1 = at lower band, 0 = at middle, +1 = at upper band)
    """
    if pd.isna(lower) or pd.isna(upper) or upper == lower:
        return 0.0

    # Calculate position relative to bands
    band_range = upper - lower
    position = (price - middle) / (band_range / 2)

    # Clamp to -1 to +1 range
    return max(-1.0, min(1.0, position))


def generate_bb_signal(
    price: float,
    lower: float,
    middle: float,
    upper: float,
    bandwidth: float
) -> str:
    """
    Generate trading signal from Bollinger Bands

    Args:
        price: Current price
        lower: Lower band value
        middle: Middle band value
        upper: Upper band value
        bandwidth: Band width (volatility)

    Returns:
        Signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
    """
    if pd.isna(price) or pd.isna(lower) or pd.isna(upper):
        return "NEUTRAL"

    position = calculate_bb_position(price, lower, middle, upper)

    # Low volatility (tight bands) - range-bound market
    is_low_volatility = bandwidth < 10 if not pd.isna(bandwidth) else False

    # Generate signal based on price position
    if price < lower:
        # Price below lower band
        if is_low_volatility:
            return "STRONG_BUY"  # Low volatility + oversold = strong signal
        else:
            return "BUY"  # Oversold
    elif price > upper:
        # Price above upper band
        if is_low_volatility:
            return "STRONG_SELL"  # Low volatility + overbought = strong signal
        else:
            return "SELL"  # Overbought
    elif position < -0.5:
        return "BUY"  # Near lower band
    elif position > 0.5:
        return "SELL"  # Near upper band
    else:
        return "NEUTRAL"  # Near middle band


def compute_bollinger(
    history: Dict[str, pd.DataFrame],
    top_spot: Optional[pd.DataFrame] = None,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands factor for all symbols

    Args:
        history: Historical price data by symbol
        top_spot: Optional spot data (unused)
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        DataFrame with Bollinger Bands values and signals
    """
    rows: List[dict] = []

    for symbol, df in history.items():
        if df is None or df.empty or len(df) < period:
            continue

        # Ensure proper date sorting
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['Date']):
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])

        df_sorted = df_copy.sort_values("Date", ascending=True).reset_index(drop=True)

        # Calculate Bollinger Bands
        middle, upper, lower, bandwidth = calculate_bollinger_bands(
            df_sorted, period, std_dev
        )

        # Get latest values
        latest_price = df_sorted['Close'].iloc[-1]
        latest_middle = middle.iloc[-1] if not middle.empty else np.nan
        latest_upper = upper.iloc[-1] if not upper.empty else np.nan
        latest_lower = lower.iloc[-1] if not lower.empty else np.nan
        latest_bandwidth = bandwidth.iloc[-1] if not bandwidth.empty else np.nan

        if pd.isna(latest_middle) or pd.isna(latest_upper) or pd.isna(latest_lower):
            continue

        # Calculate position within bands
        bb_position = calculate_bb_position(
            latest_price, latest_lower, latest_middle, latest_upper
        )

        # Generate signal
        signal = generate_bb_signal(
            latest_price, latest_lower, latest_middle, latest_upper, latest_bandwidth
        )

        # Calculate signal strength (distance from middle band)
        strength = abs(bb_position)  # 0 to 1

        rows.append({
            "Symbol": symbol,
            "BB Middle": float(latest_middle),
            "BB Upper": float(latest_upper),
            "BB Lower": float(latest_lower),
            "BB Width": float(latest_bandwidth),
            "BB Position": float(bb_position),
            "BB Signal": signal,
            "BB Strength": float(strength)
        })

    # Sort by position (most oversold first)
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        df_result = df_result.sort_values("BB Position", ascending=True)

    return df_result


BOLLINGER_FACTOR = Factor(
    id="bollinger",
    name="Bollinger Bands (20,2)",
    description="Bollinger Bands: Volatility indicator. Price < Lower Band = oversold, > Upper Band = overbought",
    columns=[
        {"key": "BB Middle", "label": "Middle Band", "type": "number", "sortable": True},
        {"key": "BB Upper", "label": "Upper Band", "type": "number", "sortable": True},
        {"key": "BB Lower", "label": "Lower Band", "type": "number", "sortable": True},
        {"key": "BB Width", "label": "Width %", "type": "number", "sortable": True},
        {"key": "BB Position", "label": "Position", "type": "number", "sortable": True},
        {"key": "BB Signal", "label": "Signal", "type": "text", "sortable": True},
        {"key": "BB Strength", "label": "Strength", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_bollinger(history, top_spot, 20, 2.0),
)

MODULE_FACTORS = [BOLLINGER_FACTOR]
