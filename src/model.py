"""CatBoost vacancy prediction model utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import shap
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit


DATA_PATH = Path("data/processed/ktx_model_input.csv")
MODEL_PATH = Path("models/catboost_model.cbm")
OUTPUT_DIR = Path("outputs/img")

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
CAT_FEATURES = ["노선", "계절"]
SHAP_DISPLAY_NAMES = {
    "월": "month",
    "분기": "quarter",
    "계절": "season",
    "코로나기간": "covid_period",
    "SRT개통후": "after_srt",
    "노선": "route",
    "공실률_lag1": "vacancy_lag1",
    "공실률_lag12": "vacancy_lag12",
    "공실률_ma3": "vacancy_ma3",
}


def load_model_input(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load model input data and apply the required ordering."""
    df = pd.read_csv(path, parse_dates=["yearmonth"])
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    return df.sort_values("yearmonth").reset_index(drop=True)


def _build_model() -> CatBoostRegressor:
    """Create a CatBoost regressor with the project baseline parameters."""
    return CatBoostRegressor(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        eval_metric="MAE",
        early_stopping_rounds=50,
        random_seed=42,
        verbose=100,
    )


def _mape(y_true: pd.Series, y_pred: Any) -> float:
    """Compute MAPE while avoiding division by zero."""
    y_true_series = pd.Series(y_true).reset_index(drop=True)
    y_pred_series = pd.Series(y_pred)
    nonzero_mask = y_true_series != 0
    return (
        ((y_true_series[nonzero_mask] - y_pred_series[nonzero_mask]).abs()
        / y_true_series[nonzero_mask].abs())
        .mean()
        * 100
    )


def train(df: pd.DataFrame) -> tuple[CatBoostRegressor, pd.DataFrame]:
    """Run walk-forward cross validation and return a final fitted model."""
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    cat_feature_indices = [X.columns.get_loc(col) for col in CAT_FEATURES]

    tscv = TimeSeriesSplit(n_splits=5)
    fold_metrics = []

    for fold, (train_idx, valid_idx) in enumerate(tscv.split(X), start=1):
        X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
        y_train, y_valid = y.iloc[train_idx], y.iloc[valid_idx]

        model = _build_model()
        model.fit(
            X_train,
            y_train,
            cat_features=cat_feature_indices,
            eval_set=(X_valid, y_valid),
            use_best_model=True,
        )
        y_pred = model.predict(X_valid)

        mae = mean_absolute_error(y_valid, y_pred)
        rmse = mean_squared_error(y_valid, y_pred) ** 0.5
        mape = _mape(y_valid, y_pred)

        fold_metrics.append(
            {"fold": fold, "MAE": mae, "MAPE": mape, "RMSE": rmse}
        )
        print(
            f"fold {fold}: MAE={mae:.4f}, MAPE={mape:.2f}%, RMSE={rmse:.4f}"
        )

    metrics_df = pd.DataFrame(fold_metrics)
    mean_metrics = metrics_df[["MAE", "MAPE", "RMSE"]].mean()
    print("\nmean metrics")
    print(mean_metrics.round(4).to_string())

    final_model = _build_model()
    final_model.fit(X, y, cat_features=cat_feature_indices)
    return final_model, metrics_df


def evaluate(
    model: CatBoostRegressor,
    df: pd.DataFrame,
    output_dir: Path = OUTPUT_DIR,
) -> pd.DataFrame:
    """Save prediction and SHAP diagnostics for a fitted model."""
    output_dir.mkdir(parents=True, exist_ok=True)
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    y_pred = model.predict(X)

    pred_df = df[["yearmonth", "노선", TARGET_COL]].copy()
    pred_df["예측공실률"] = y_pred

    plt.figure(figsize=(8, 8))
    plt.scatter(y, y_pred, alpha=0.65)
    min_value = min(y.min(), y_pred.min())
    max_value = max(y.max(), y_pred.max())
    plt.plot([min_value, max_value], [min_value, max_value], "r--")
    plt.xlabel("Actual vacancy rate")
    plt.ylabel("Predicted vacancy rate")
    plt.title("Predicted vs Actual Vacancy Rate")
    plt.tight_layout()
    plt.savefig(output_dir / "pred_vs_actual.png", dpi=200)
    plt.close()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    X_display = X.rename(columns=SHAP_DISPLAY_NAMES)
    shap.summary_plot(shap_values, X_display, show=False)
    plt.tight_layout()
    plt.savefig(output_dir / "shap_summary.png", dpi=200, bbox_inches="tight")
    plt.close()

    return pred_df


def predict(model: CatBoostRegressor, X: pd.DataFrame) -> pd.Series:
    """Predict vacancy rates for feature rows."""
    return pd.Series(model.predict(X[FEATURE_COLS]), index=X.index, name="예측공실률")


def main() -> None:
    """Train the CatBoost model and save model artifacts."""
    df = load_model_input()
    print(f"data shape: {df.shape}")
    print(f"feature_cols = {FEATURE_COLS}")
    print(f"target_col = {TARGET_COL!r}")
    print(f"cat_features = {CAT_FEATURES}")

    model, metrics_df = train(df)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH)
    print(f"saved model: {MODEL_PATH}")

    evaluate(model, df)
    print(f"saved plot: outputs/img/pred_vs_actual.png")
    print(f"saved plot: outputs/img/shap_summary.png")
    print("\nfold metrics")
    print(metrics_df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
