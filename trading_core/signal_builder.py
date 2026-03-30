import pandas as pd
from typing import Dict, Any, Optional

from trading_core.patterns import Patterns
from trading_core.volatility import Volatility
from trading_core.trend import Trend
from trading_core.zones import Zones
from trading_core.zone_detector import ZoneDetector
from trading_core.confluence import ConfluenceEngine


class SignalBuilder:
    """
    Unified logic for computing:
    - candle anatomy
    - patterns
    - volatility
    - swings
    - trend
    - zones
    - confluence
    - scoring
    - direction
    - confidence

    Used by both:
    - HistoricalSignalGenerator (loop over all candles)
    - LiveSignalGenerator (compute only last candle)
    """

    @staticmethod
    def compute_candle_anatomy(df: pd.DataFrame) -> pd.DataFrame:
        df["body_size"] = (df["close"] - df["open"]).abs()
        df["range"] = df["high"] - df["low"]
        df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
        return df

    @staticmethod
    def compute_patterns(df: pd.DataFrame) -> pd.DataFrame:
        return Patterns.detect_all(df)

    @staticmethod
    def compute_volatility(df: pd.DataFrame, vol_cfg: Dict[str, Any]) -> pd.DataFrame:
        return Volatility.compute_all(df, vol_cfg)

    @staticmethod
    def compute_swings(df: pd.DataFrame, left: int, right: int) -> pd.DataFrame:
        return Zones.find_swings(df, left=left, right=right)

    @staticmethod
    def compute_trend(df: pd.DataFrame, trend_cfg: Dict[str, Any]) -> pd.DataFrame:
        return Trend.compute_all(df, trend_cfg)

    @staticmethod
    def compute_zones(df: pd.DataFrame, left: int, right: int, tolerance: float):
        return ZoneDetector.detect_zones(df, left, right, tolerance)

    @staticmethod
    def compute_confluence(
        df: pd.DataFrame,
        symbol_cfg: Dict[str, Any],
        zones,
        tolerance: float
    ) -> Dict[str, int]:
        """
        Compute confluence for the LAST candle in df.
        """
        return ConfluenceEngine.compute_total(df, symbol_cfg, zones, tolerance)

    @staticmethod
    def compute_direction(total_score: int) -> str:
        if total_score > 0:
            return "long"
        if total_score < 0:
            return "short"
        return "neutral"

    @staticmethod
    def compute_confidence(total_score: int, max_score: int = 6) -> float:
        return min(1.0, abs(total_score) / max_score)

    @staticmethod
    def build_signal(
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        confluence: Dict[str, int],
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Returns a DICT with all signal fields.
        The research/live project can wrap this into a Signal dataclass.
        """
        last = df.iloc[-1]
        total = confluence["total"]

        direction = SignalBuilder.compute_direction(total)
        confidence = SignalBuilder.compute_confidence(total)

        metadata = {"timestamp": last.name}
        if extra_metadata:
            metadata.update(extra_metadata)

        return {
            "symbol": symbol,
            "direction": direction,
            "total_score": total,
            "pattern_score": confluence["pattern_score"],
            "zone_score": confluence["zone_score"],
            "volatility_score": confluence["volatility_score"],
            "trend_score": confluence["trend_score"],
            "confidence": confidence,
            "price": last["close"],
            "timeframe": str(timeframe),
            "metadata": metadata,
        }

    # ---------------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------------
    @staticmethod
    def compute_all(
            df,
            symbol,
            timeframe,
            symbol_cfg,
            left=None,
            right=None,
            tolerance=None,
            extra_metadata=None,
    ):
        df = df.copy()

        # -----------------------------
        # ZONES CONFIG
        # -----------------------------
        zones_cfg = symbol_cfg.get("zones", {})
        left = left if left is not None else zones_cfg.get("left", 3)
        right = right if right is not None else zones_cfg.get("right", 3)
        tolerance = tolerance if tolerance is not None else zones_cfg.get("tolerance", 0.0005)
        tolerance = float(tolerance)

        # -----------------------------
        # VOLATILITY CONFIG
        # -----------------------------
        vol_cfg = symbol_cfg.get("volatility", {
            "atr_period": 14,
            "percentile_window": 200,
            "expansion_factor": 1.5,
            "compression_factor": 0.7,
        })

        # -----------------------------
        # TREND CONFIG
        # -----------------------------
        trend_cfg = symbol_cfg.get("trend", {
            "ma_fast": 20,
            "ma_slow": 50,
            "swing_lookback": 10,
        })

        # Always enforce swing column names
        trend_cfg["swing_high_col"] = "is_swing_high"
        trend_cfg["swing_low_col"] = "is_swing_low"

        # -----------------------------
        # 1) Candle anatomy
        # -----------------------------
        df = SignalBuilder.compute_candle_anatomy(df)

        # -----------------------------
        # 2) Patterns
        # -----------------------------
        df = SignalBuilder.compute_patterns(df)

        # -----------------------------
        # 3) Volatility
        # -----------------------------
        df = SignalBuilder.compute_volatility(df, vol_cfg)

        # -----------------------------
        # 4) Swings
        # -----------------------------
        df = SignalBuilder.compute_swings(df, left, right)

        # -----------------------------
        # 5) Trend
        # -----------------------------
        df = SignalBuilder.compute_trend(df, trend_cfg)

        # -----------------------------
        # 6) Zones
        # -----------------------------
        zones = SignalBuilder.compute_zones(df, left, right, tolerance)

        # -----------------------------
        # 7) Confluence (last candle)
        # -----------------------------
        confluence = SignalBuilder.compute_confluence(df, symbol_cfg, zones, tolerance)

        # -----------------------------
        # 8) Build final signal dict
        # -----------------------------
        return SignalBuilder.build_signal(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            confluence=confluence,
            extra_metadata=extra_metadata,
        )

        # then use vol_cfg, trend_cfg, left/right/tolerance as before

    # @staticmethod
    # def compute_all(
    #     df: pd.DataFrame,
    #     symbol: str,
    #     timeframe: str,
    #     symbol_cfg: Dict[str, Any],
    #     left: int = 3,
    #     right: int = 3,
    #     tolerance: float = 0.0005,
    #     vol_cfg: Optional[Dict[str, Any]] = None,
    #     trend_cfg: Optional[Dict[str, Any]] = None,
    #     extra_metadata: Optional[Dict[str, Any]] = None,
    # ) -> Dict[str, Any]:
    #     """
    #     Compute EVERYTHING for the last candle of df.
    #     This is used by both historical and live generators.
    #     """
    #
    #     df = df.copy()
    #
    #     # 1) Candle anatomy
    #     df = SignalBuilder.compute_candle_anatomy(df)
    #
    #     # 2) Patterns
    #     df = SignalBuilder.compute_patterns(df)
    #
    #     # 3) Volatility
    #     if vol_cfg is None:
    #         vol_cfg = {
    #             "atr_period": 14,
    #             "percentile_window": 200,
    #             "expansion_factor": 1.5,
    #             "compression_factor": 0.7,
    #         }
    #     df = SignalBuilder.compute_volatility(df, vol_cfg)
    #
    #     # 4) Swings
    #     df = SignalBuilder.compute_swings(df, left, right)
    #
    #     # 5) Trend
    #     if trend_cfg is None:
    #         trend_cfg = {
    #             "ma_fast": 20,
    #             "ma_slow": 50,
    #             "swing_high_col": "is_swing_high",
    #             "swing_low_col": "is_swing_low",
    #             "swing_lookback": 10,
    #         }
    #     df = SignalBuilder.compute_trend(df, trend_cfg)
    #
    #     # 6) Zones
    #     zones = SignalBuilder.compute_zones(df, left, right, tolerance)
    #
    #     # 7) Confluence (last candle)
    #     confluence = SignalBuilder.compute_confluence(df, symbol_cfg, zones, tolerance)
    #
    #     # 8) Build final signal dict
    #     return SignalBuilder.build_signal(
    #         df=df,
    #         symbol=symbol,
    #         timeframe=timeframe,
    #         confluence=confluence,
    #         extra_metadata=extra_metadata,
    #     )
