import pandas as pd
from typing import Dict, Any, Optional

from trading_core.signal_builder import SignalBuilder


class LiveSignalGenerator:
    """
    Thin wrapper around SignalBuilder for live trading.
    Computes the signal ONLY for the last candle of the dataframe.
    """

    def __init__(self, symbol_cfg: Dict[str, Any], left=3, right=3, tolerance=0.0005):
        self.symbol_cfg = symbol_cfg
        self.left = left
        self.right = right
        self.tolerance = tolerance

    def generate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute the signal for the last candle in df.
        Returns a DICT with:
            - direction
            - total_score
            - pattern_score
            - zone_score
            - volatility_score
            - trend_score
            - confidence
            - price
            - metadata
        """

        if len(df) < 50:
            raise ValueError("Not enough candles to compute live signal")

        return SignalBuilder.compute_all(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            symbol_cfg=self.symbol_cfg,
            left=self.left,
            right=self.right,
            tolerance=self.tolerance,
            extra_metadata=extra_metadata,
        )
