"""
Confluence Calculator Service

This module calculates technical indicators for symbols and generates
confluence-based trading signals. It serves as the bridge between
raw price data and AI trading decisions.

Usage:
    calculator = ConfluenceCalculator()
    analysis = calculator.calculate_for_symbols(["BTC", "ETH"], price_history)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
import pandas as pd

from factors.rsi import compute_rsi
from factors.macd import compute_macd
from factors.bollinger import compute_bollinger
from factors.ema import compute_ema
from factors.atr import compute_atr
from services.signal_generator import SignalGenerator, generate_signals_for_symbol

logger = logging.getLogger(__name__)


class ConfluenceCalculator:
    """
    Calculate technical indicators and generate confluence-based signals
    """

    def __init__(self, signal_generator: Optional[SignalGenerator] = None):
        """
        Initialize confluence calculator

        Args:
            signal_generator: Custom signal generator (optional)
        """
        self.signal_generator = signal_generator or SignalGenerator()

    def calculate_all_indicators(
        self,
        history: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Calculate all technical indicators for given price history

        Args:
            history: Dict mapping symbol to DataFrame with OHLCV data

        Returns:
            DataFrame with all indicators merged by symbol
        """
        if not history:
            return pd.DataFrame()

        indicator_dfs = []

        try:
            # Calculate each indicator
            logger.debug("Calculating RSI...")
            rsi_df = compute_rsi(history, None)
            if not rsi_df.empty:
                indicator_dfs.append(rsi_df)

            logger.debug("Calculating MACD...")
            macd_df = compute_macd(history, None)
            if not macd_df.empty:
                indicator_dfs.append(macd_df)

            logger.debug("Calculating Bollinger Bands...")
            bb_df = compute_bollinger(history, None)
            if not bb_df.empty:
                indicator_dfs.append(bb_df)

            logger.debug("Calculating EMA...")
            ema_df = compute_ema(history, None)
            if not ema_df.empty:
                indicator_dfs.append(ema_df)

            logger.debug("Calculating ATR...")
            atr_df = compute_atr(history, None)
            if not atr_df.empty:
                indicator_dfs.append(atr_df)

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return pd.DataFrame()

        if not indicator_dfs:
            logger.warning("No indicators could be calculated")
            return pd.DataFrame()

        # Merge all indicators on Symbol
        result = indicator_dfs[0]
        for df in indicator_dfs[1:]:
            result = result.merge(df, on='Symbol', how='outer')

        logger.info(f"Calculated indicators for {len(result)} symbols")
        return result

    def calculate_for_symbols(
        self,
        symbols: List[str],
        history: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Calculate indicators and signals for specific symbols

        Args:
            symbols: List of symbols to analyze
            history: Price history dict

        Returns:
            Dict mapping symbol to signal analysis
        """
        # Calculate all indicators
        indicators_df = self.calculate_all_indicators(history)

        if indicators_df.empty:
            logger.warning("No indicators calculated")
            return {}

        # Generate signals for each requested symbol
        results = {}
        for symbol in symbols:
            # Get indicator data for this symbol
            symbol_data = indicators_df[indicators_df['Symbol'] == symbol]

            if symbol_data.empty:
                logger.warning(f"No indicator data for {symbol}")
                continue

            # Convert to dict
            symbol_dict = symbol_data.iloc[0].to_dict()

            # Generate signals
            signals = self.signal_generator.generate_signals(symbol_dict)
            results[symbol] = signals

        return results

    def format_for_ai_prompt(
        self,
        symbol: str,
        signals: Dict[str, Any]
    ) -> str:
        """
        Format signal analysis for AI prompt

        Args:
            symbol: Symbol name
            signals: Signal analysis from generate_signals()

        Returns:
            Formatted string for AI prompt
        """
        lines = [
            f"=== TECHNICAL ANALYSIS: {symbol} ===",
            "",
            f"Overall Signal: {signals['overall_signal']} (Strength: {signals['strength']*100:.0f}%)",
            f"Confluence: {signals['agreement_pct']:.0f}% agreement",
            f"Indicators: {signals['buy_count']} BUY, {signals['sell_count']} SELL, {signals['neutral_count']} NEUTRAL",
            ""
        ]

        # Individual indicator signals
        lines.append("Indicator Readings:")
        raw_signals = signals.get('raw_signals', {})
        for indicator_name, signal_data in raw_signals.items():
            signal = signal_data['signal']
            value = signal_data.get('value', 'N/A')

            # Format value based on type
            if isinstance(value, (int, float)):
                value_str = f"{value:.2f}"
            else:
                value_str = str(value)

            lines.append(f"  - {indicator_name}: {signal} (value: {value_str})")

        # Agreeing vs conflicting
        lines.extend([
            "",
            f"Agreeing Indicators: {', '.join(signals['agreeing_indicators']) if signals['agreeing_indicators'] else 'None'}",
            f"Conflicting Indicators: {', '.join(signals['conflicting_indicators']) if signals['conflicting_indicators'] else 'None'}",
        ])

        # Risk context from ATR
        risk_context = signals.get('risk_context')
        if risk_context:
            lines.extend([
                "",
                f"Risk Management:",
                f"  - Volatility: {risk_context['volatility']}",
                f"  - ATR: {risk_context['atr_pct']:.2f}% of price",
                f"  - Suggested Position Size: {risk_context['position_multiplier']*100:.0f}% of normal",
                f"  - Suggested Stop Loss: {risk_context['suggested_stop_loss_pct']:.2f}%",
                f"  - Suggested Take Profit: {risk_context['suggested_take_profit_pct']:.2f}%"
            ])

        return "\n".join(lines)

    def format_multi_symbol_for_ai(
        self,
        symbol_signals: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Format multiple symbol analyses for AI prompt

        Args:
            symbol_signals: Dict mapping symbol to signals

        Returns:
            Formatted string for AI prompt
        """
        if not symbol_signals:
            return "No technical analysis available."

        sections = []
        for symbol, signals in symbol_signals.items():
            section = self.format_for_ai_prompt(symbol, signals)
            sections.append(section)

        return "\n\n".join(sections)


# Global confluence calculator instance
default_confluence_calculator = ConfluenceCalculator()


def calculate_confluence_for_symbols(
    symbols: List[str],
    history: Dict[str, pd.DataFrame],
    calculator: Optional[ConfluenceCalculator] = None
) -> Dict[str, Any]:
    """
    Helper function to calculate confluence for symbols

    Args:
        symbols: List of symbols
        history: Price history dict
        calculator: Custom calculator (optional)

    Returns:
        Dict mapping symbol to signals
    """
    if calculator is None:
        calculator = default_confluence_calculator

    return calculator.calculate_for_symbols(symbols, history)


def format_confluence_for_ai(
    symbol_signals: Dict[str, Dict[str, Any]],
    calculator: Optional[ConfluenceCalculator] = None
) -> str:
    """
    Helper function to format confluence analysis for AI

    Args:
        symbol_signals: Symbol signals dict
        calculator: Custom calculator (optional)

    Returns:
        Formatted string
    """
    if calculator is None:
        calculator = default_confluence_calculator

    return calculator.format_multi_symbol_for_ai(symbol_signals)
