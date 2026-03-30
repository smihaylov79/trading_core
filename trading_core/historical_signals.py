import pandas as pd
from typing import Dict, Any

from trading_core.signal_builder import SignalBuilder
from trading_core.patterns import Patterns
from trading_core.volatility import Volatility
from trading_core.trend import Trend
from trading_core.zones import Zones
from trading_core.zone_detector import ZoneDetector
from trading_core.confluence import ConfluenceEngine


class HistoricalSignalGenerator:

    def __init__(self, symbol_cfg: Dict[str, Any], left=3, right=3, tolerance=0.0005):
        self.symbol_cfg = symbol_cfg
        self.left = left
        self.right = right
        self.tolerance = tolerance

    def generate(self, df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
        df = df.copy()

        # ---------------------------------------------------------
        # PHASE 1 — PRECOMPUTE EVERYTHING ONCE
        # ---------------------------------------------------------

        # Candle anatomy
        df = SignalBuilder.compute_candle_anatomy(df)

        # Patterns
        df = Patterns.detect_all(df)

        # Volatility
        vol_cfg = {
            "atr_period": 14,
            "percentile_window": 200,
            "expansion_factor": 1.5,
            "compression_factor": 0.7,
        }
        df = Volatility.compute_all(df, vol_cfg)

        # Swings
        df = Zones.find_swings(df, left=self.left, right=self.right)

        # Trend
        trend_cfg = {
            "ma_fast": 20,
            "ma_slow": 50,
            "swing_high_col": "is_swing_high",
            "swing_low_col": "is_swing_low",
            "swing_lookback": 10,
        }
        df = Trend.compute_all(df, trend_cfg)

        # Zones (computed once)
        zones = ZoneDetector.detect_zones(df, self.left, self.right, self.tolerance)

        # Prepare output columns
        df["pattern_score"] = 0
        df["zone_score"] = 0
        df["volatility_score"] = 0
        df["trend_score"] = 0
        df["total_score"] = 0
        df["confidence"] = 0.0
        df["signal"] = 0

        # ---------------------------------------------------------
        # PHASE 2 — LOOP ONLY FOR CONFLUENCE + SIGNAL
        # ---------------------------------------------------------
        for i in range(len(df)):
            window = df.iloc[: i + 1]

            conf = ConfluenceEngine.compute_total(
                window,
                self.symbol_cfg,
                zones,
                self.tolerance
            )

            df.at[df.index[i], "pattern_score"] = conf["pattern_score"]
            df.at[df.index[i], "zone_score"] = conf["zone_score"]
            df.at[df.index[i], "volatility_score"] = conf["volatility_score"]
            df.at[df.index[i], "trend_score"] = conf["trend_score"]
            df.at[df.index[i], "total_score"] = conf["total"]

            # Confidence
            df.at[df.index[i], "confidence"] = abs(conf["total"]) / 6

            # Signal
            if conf["total"] > 0:
                df.at[df.index[i], "signal"] = 1
            elif conf["total"] < 0:
                df.at[df.index[i], "signal"] = -1
            else:
                df.at[df.index[i], "signal"] = 0

        return df



# from trading_core.patterns import Patterns
# from trading_core.volatility import Volatility
# from trading_core.trend import Trend
# from trading_core.zone_detector import ZoneDetector
# from trading_core.confluence import ConfluenceEngine
# from trading_core.zones import Zones
#
#
#
# class HistoricalSignalGenerator:
#
#     def __init__(self, symbol_cfg, left=3, right=3, tolerance=0.0005):
#         self.symbol_cfg = symbol_cfg
#         self.left = left
#         self.right = right
#         self.tolerance = tolerance
#
#     def generate(self, df, symbol, timeframe):
#         df = df.copy()
#
#         # ---------------------------------------------------------
#         # 1) Candle anatomy (required for patterns)
#         # ---------------------------------------------------------
#         df["body_size"] = (df["close"] - df["open"]).abs()
#         df["range"] = df["high"] - df["low"]
#         df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
#         df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
#
#         # ---------------------------------------------------------
#         # 2) Patterns (same as tests)
#         # ---------------------------------------------------------
#         df = Patterns.detect_all(df)
#
#         # ---------------------------------------------------------
#         # 3) Volatility (same as tests)
#         # ---------------------------------------------------------
#         vol_cfg = {
#             "atr_period": 14,
#             "percentile_window": 200,
#             "expansion_factor": 1.5,
#             "compression_factor": 0.7,
#         }
#         df = Volatility.compute_all(df, vol_cfg)
#
#         # 4) Swings (needed for trend)
#         df = Zones.find_swings(df, left=self.left, right=self.right)
#
#         # 5) Trend
#         trend_cfg = {
#             "ma_fast": 20,
#             "ma_slow": 50,
#             "swing_high_col": "is_swing_high",
#             "swing_low_col": "is_swing_low",
#             "swing_lookback": 10,
#         }
#
#         df = Trend.compute_all(df, trend_cfg)
#
#         # 6) Zones
#         zones = ZoneDetector.detect_zones(df, self.left, self.right, self.tolerance)
#
#         # ---------------------------------------------------------
#         # 6) Confluence per candle
#         # ---------------------------------------------------------
#         pattern_scores = []
#         zone_scores = []
#         vol_scores = []
#         trend_scores = []
#         total_scores = []
#
#         for i in range(len(df)):
#             window = df.iloc[: i + 1]
#             conf = ConfluenceEngine.compute_total(window, self.symbol_cfg, zones, self.tolerance)
#
#             pattern_scores.append(conf["pattern_score"])
#             zone_scores.append(conf["zone_score"])
#             vol_scores.append(conf["volatility_score"])
#             trend_scores.append(conf["trend_score"])
#             total_scores.append(conf["total"])
#
#         df["pattern_score"] = pattern_scores
#         df["zone_score"] = zone_scores
#         df["volatility_score"] = vol_scores
#         df["trend_score"] = trend_scores
#         df["total_score"] = total_scores
#         df["confidence"] = df["total_score"].abs() / 6
#
#         # ---------------------------------------------------------
#         # 7) Signal
#         # ---------------------------------------------------------
#         df["signal"] = 0
#         df.loc[df["total_score"] > 0, "signal"] = 1
#         df.loc[df["total_score"] < 0, "signal"] = -1
#
#         return df
