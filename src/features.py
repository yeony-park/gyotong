"""Feature engineering utilities for KTX vacancy prediction."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/processed/ktx_long.csv")
OUTPUT_PATH = Path("data/processed/ktx_model_input.csv")

FEATURE_COLS = [
    "월",
    "분기",
    "계절",
    "코로나기간",
    "SRT개통후",
    "노선",
    "공실률_lag1",
    "공실률_lag12",
    "공실률_ma3",
]
TARGET_COL = "공실률"
LAG_COLS = ["공실률_lag1", "공실률_lag12", "공실률_ma3"]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create model input features from the KTX long-format dataset."""
    feature_df = df.copy()

    if "개통전" in feature_df.columns:
        feature_df = feature_df[feature_df["개통전"] != 1].copy()

    feature_df = feature_df.sort_values(["노선", "yearmonth"]).copy()
    route_groups = feature_df.groupby("노선")["공실률"]

    feature_df["공실률_lag1"] = route_groups.shift(1)
    feature_df["공실률_lag12"] = route_groups.shift(12)
    feature_df["공실률_ma3"] = route_groups.transform(
        lambda x: x.shift(1).rolling(3).mean()
    )

    feature_df = feature_df.dropna(subset=LAG_COLS).copy()
    return feature_df


def main() -> None:
    """Build and save the model input dataset."""
    df = pd.read_csv(DATA_PATH, parse_dates=["yearmonth"])
    model_df = make_features(df)
    model_df.to_csv(OUTPUT_PATH, index=True, encoding="utf-8-sig")

    print(f"feature_cols = {FEATURE_COLS}")
    print(f"target_col = {TARGET_COL!r}")
    print(f"final shape: {model_df.shape}")
    print(f"saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
