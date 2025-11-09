"""
Signal Generator Service

This module generates trading signals from technical indicators with
multi-indicator confluence analysis.

Signal Types:
    - STRONG_BUY: Strong bullish confluence (>= 75% agreement)
    - BUY: Bullish confluence (>= 60% agreement)
    - NEUTRAL: No clear consensus (< 60% agreement either way)
    - SELL: Bearish confluence (>= 60% agreement)
    - STRONG_SELL: Strong bearish confluence (>= 75% agreement)

Confluence is calculated by:
    1. Converting each indicator to a directional signal
    2. Counting BUY/SELL/NEUTRAL votes
    3. Applying weighted voting (some indicators have higher weight)
    4. Determining overall signal based on agreement threshold
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    """Signal direction enumeration"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class IndicatorCategory(str, Enum):
    """Indicator category for classification"""
    MOMENTUM = "momentum"
    TREND = "trend"
    VOLATILITY = "volatility"
    VOLUME = "volume"


# Default indicator weights (can be customized)
DEFAULT_INDICATOR_WEIGHTS = {
    "RSI": 0.20,        # 20% - Momentum
    "MACD": 0.25,       # 25% - Trend (highest weight)
    "Bollinger": 0.20,  # 20% - Volatility
    "EMA": 0.25,        # 25% - Trend (highest weight)
    "Momentum": 0.05,   # 5% - Custom momentum
    "Support": 0.05,    # 5% - Custom support
}


class SignalGenerator:
    """
    Generate trading signals from technical indicators with confluence analysis
    """

    def __init__(self, indicator_weights: Optional[Dict[str, float]] = None):
        """
        Initialize signal generator

        Args:
            indicator_weights: Custom indicator weights (optional)
        """
        self.weights = indicator_weights or DEFAULT_INDICATOR_WEIGHTS

    def normalize_signal_to_score(self, signal: str) -> float:
        """
        Convert signal string to numeric score

        Args:
            signal: Signal string (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL)

        Returns:
            Score: -1.0 to +1.0 (-1 = strong sell, 0 = neutral, +1 = strong buy)
        """
        signal_scores = {
            "STRONG_BUY": 1.0,
            "BUY": 0.5,
            "NEUTRAL": 0.0,
            "SELL": -0.5,
            "STRONG_SELL": -1.0
        }
        return signal_scores.get(signal, 0.0)

    def convert_indicator_signals(self, indicator_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Convert raw indicator data to signal format

        Args:
            indicator_data: Raw indicator values

        Returns:
            Dict of indicator signals with metadata
        """
        signals = {}

        # RSI Signal
        if "RSI" in indicator_data and "RSI Signal" in indicator_data:
            signals["RSI"] = {
                "signal": indicator_data["RSI Signal"],
                "value": indicator_data["RSI"],
                "score": self.normalize_signal_to_score(indicator_data["RSI Signal"]),
                "category": IndicatorCategory.MOMENTUM,
                "weight": self.weights.get("RSI", 0.2)
            }

        # MACD Signal
        if "MACD Direction" in indicator_data:
            signals["MACD"] = {
                "signal": indicator_data["MACD Direction"],
                "value": indicator_data.get("MACD Histogram", 0),
                "score": self.normalize_signal_to_score(indicator_data["MACD Direction"]),
                "category": IndicatorCategory.TREND,
                "weight": self.weights.get("MACD", 0.25)
            }

        # Bollinger Bands Signal
        if "BB Signal" in indicator_data:
            signals["Bollinger"] = {
                "signal": indicator_data["BB Signal"],
                "value": indicator_data.get("BB Position", 0),
                "score": self.normalize_signal_to_score(indicator_data["BB Signal"]),
                "category": IndicatorCategory.VOLATILITY,
                "weight": self.weights.get("Bollinger", 0.2)
            }

        # EMA Signal
        if "EMA Signal" in indicator_data:
            signals["EMA"] = {
                "signal": indicator_data["EMA Signal"],
                "value": indicator_data.get("Trend", "NEUTRAL"),
                "score": self.normalize_signal_to_score(indicator_data["EMA Signal"]),
                "category": IndicatorCategory.TREND,
                "weight": self.weights.get("EMA", 0.25)
            }

        # Momentum Signal (custom)
        if "Momentum Score" in indicator_data:
            # Convert momentum score (0-1) to signal
            momentum_score = indicator_data["Momentum Score"]
            if momentum_score > 0.7:
                momentum_signal = "BUY"
            elif momentum_score > 0.6:
                momentum_signal = "NEUTRAL"
            elif momentum_score < 0.3:
                momentum_signal = "SELL"
            elif momentum_score < 0.4:
                momentum_signal = "NEUTRAL"
            else:
                momentum_signal = "NEUTRAL"

            signals["Momentum"] = {
                "signal": momentum_signal,
                "value": momentum_score,
                "score": self.normalize_signal_to_score(momentum_signal),
                "category": IndicatorCategory.MOMENTUM,
                "weight": self.weights.get("Momentum", 0.05)
            }

        # Support Signal (custom)
        if "Support Score" in indicator_data:
            # Convert support score (0-1) to signal
            support_score = indicator_data["Support Score"]
            if support_score > 0.7:
                support_signal = "BUY"
            elif support_score > 0.6:
                support_signal = "NEUTRAL"
            elif support_score < 0.3:
                support_signal = "SELL"
            elif support_score < 0.4:
                support_signal = "NEUTRAL"
            else:
                support_signal = "NEUTRAL"

            signals["Support"] = {
                "signal": support_signal,
                "value": support_score,
                "score": self.normalize_signal_to_score(support_signal),
                "category": IndicatorCategory.TREND,
                "weight": self.weights.get("Support", 0.05)
            }

        return signals

    def calculate_confluence(self, signals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate confluence score from multiple indicators

        Args:
            signals: Dict of indicator signals

        Returns:
            Confluence analysis with overall signal and strength
        """
        if not signals:
            return {
                "overall_signal": SignalDirection.NEUTRAL,
                "strength": 0.0,
                "confidence": 0.0,
                "buy_count": 0,
                "sell_count": 0,
                "neutral_count": 0,
                "total_indicators": 0,
                "weighted_score": 0.0,
                "agreeing_indicators": [],
                "conflicting_indicators": [],
                "signals_by_category": {}
            }

        # Count signals
        buy_signals = []
        sell_signals = []
        neutral_signals = []

        # Calculate weighted score
        total_weight = 0.0
        weighted_score = 0.0

        for indicator_name, signal_data in signals.items():
            signal = signal_data["signal"]
            weight = signal_data.get("weight", 1.0)
            score = signal_data.get("score", 0.0)

            # Categorize signal
            if signal in ["STRONG_BUY", "BUY"]:
                buy_signals.append(indicator_name)
            elif signal in ["STRONG_SELL", "SELL"]:
                sell_signals.append(indicator_name)
            else:
                neutral_signals.append(indicator_name)

            # Add to weighted score
            weighted_score += score * weight
            total_weight += weight

        # Normalize weighted score
        if total_weight > 0:
            weighted_score = weighted_score / total_weight
        else:
            weighted_score = 0.0

        # Calculate agreement percentage
        total_indicators = len(signals)
        buy_pct = len(buy_signals) / total_indicators if total_indicators > 0 else 0
        sell_pct = len(sell_signals) / total_indicators if total_indicators > 0 else 0

        # Determine overall signal based on weighted score and agreement
        if weighted_score >= 0.75 and buy_pct >= 0.60:
            overall_signal = SignalDirection.STRONG_BUY
            strength = weighted_score
        elif weighted_score >= 0.35 and buy_pct >= 0.50:
            overall_signal = SignalDirection.BUY
            strength = weighted_score
        elif weighted_score <= -0.75 and sell_pct >= 0.60:
            overall_signal = SignalDirection.STRONG_SELL
            strength = abs(weighted_score)
        elif weighted_score <= -0.35 and sell_pct >= 0.50:
            overall_signal = SignalDirection.SELL
            strength = abs(weighted_score)
        else:
            overall_signal = SignalDirection.NEUTRAL
            strength = abs(weighted_score)

        # Calculate confidence (how much agreement there is)
        confidence = max(buy_pct, sell_pct)

        # Identify agreeing vs conflicting indicators
        if overall_signal in [SignalDirection.STRONG_BUY, SignalDirection.BUY]:
            agreeing = buy_signals
            conflicting = sell_signals
        elif overall_signal in [SignalDirection.STRONG_SELL, SignalDirection.SELL]:
            agreeing = sell_signals
            conflicting = buy_signals
        else:
            agreeing = neutral_signals
            conflicting = buy_signals + sell_signals

        # Group by category
        signals_by_category = {}
        for indicator_name, signal_data in signals.items():
            category = signal_data.get("category", "unknown")
            if category not in signals_by_category:
                signals_by_category[category] = []
            signals_by_category[category].append({
                "indicator": indicator_name,
                "signal": signal_data["signal"],
                "score": signal_data["score"]
            })

        return {
            "overall_signal": overall_signal,
            "strength": float(strength),
            "confidence": float(confidence),
            "buy_count": len(buy_signals),
            "sell_count": len(sell_signals),
            "neutral_count": len(neutral_signals),
            "total_indicators": total_indicators,
            "weighted_score": float(weighted_score),
            "agreement_pct": float(max(buy_pct, sell_pct) * 100),
            "agreeing_indicators": agreeing,
            "conflicting_indicators": conflicting,
            "signals_by_category": signals_by_category,
            "raw_signals": signals
        }

    def generate_signals(self, indicator_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals from indicator data

        Args:
            indicator_data: Raw indicator values for a symbol

        Returns:
            Complete signal analysis with confluence
        """
        # Convert indicators to signals
        signals = self.convert_indicator_signals(indicator_data)

        # Calculate confluence
        confluence = self.calculate_confluence(signals)

        # Add risk management context from ATR
        if "ATR %" in indicator_data:
            atr_pct = indicator_data["ATR %"]
            volatility = indicator_data.get("Volatility", "NORMAL")
            position_multiplier = indicator_data.get("Position Multiplier", 1.0)

            confluence["risk_context"] = {
                "atr_pct": float(atr_pct),
                "volatility": volatility,
                "position_multiplier": float(position_multiplier),
                "suggested_stop_loss_pct": float(atr_pct * 2),  # 2x ATR for stop loss
                "suggested_take_profit_pct": float(atr_pct * 3)  # 3x ATR for take profit
            }
        else:
            confluence["risk_context"] = None

        return confluence


def generate_signals_for_symbol(
    symbol: str,
    all_indicators: Dict[str, Any],
    signal_generator: Optional[SignalGenerator] = None
) -> Optional[Dict[str, Any]]:
    """
    Generate signals for a single symbol from combined indicator data

    Args:
        symbol: Symbol to generate signals for
        all_indicators: Combined indicator data (merged from all factors)
        signal_generator: Custom signal generator (optional)

    Returns:
        Signal analysis for the symbol
    """
    if signal_generator is None:
        signal_generator = SignalGenerator()

    # Find data for this symbol
    symbol_data = None
    if isinstance(all_indicators, list):
        for row in all_indicators:
            if row.get("Symbol") == symbol:
                symbol_data = row
                break
    elif isinstance(all_indicators, dict):
        symbol_data = all_indicators.get(symbol)

    if not symbol_data:
        logger.warning(f"No indicator data found for symbol {symbol}")
        return None

    # Generate signals
    try:
        signals = signal_generator.generate_signals(symbol_data)
        signals["symbol"] = symbol
        return signals
    except Exception as e:
        logger.error(f"Error generating signals for {symbol}: {e}")
        return None


# Global signal generator instance
default_signal_generator = SignalGenerator()
