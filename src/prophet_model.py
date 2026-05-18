"""Part 4: Prophet time-series vacancy-rate forecasting by KTX route."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT_DIR / ".matplotlib"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import numpy as np
import pandas as pd


DATA_PATH = Path("data/processed/ktx_model_input.csv")
FORECAST_PATH = Path("data/processed/part4_prophet_forecast.csv")
COMPARISON_PATH = Path("data/processed/part4_prophet_vacancy_comparison.csv")
METRICS_PATH = Path("data/processed/part4_prophet_metrics.csv")
IMG_DIR = Path("outputs/img")

DEFAULT_TARGET = "공실률"
DATE_COL = "yearmonth"
ROUTE_COL = "노선"


@dataclass(frozen=True)
class ForecastConfig:
    target_col: str = DEFAULT_TARGET
    horizon_months: int = 12
    test_months: int = 12


def load_model_input(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load Part 3 model input as the shared base dataset for Part 4."""
    df = pd.read_csv(path, parse_dates=[DATE_COL])
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    return df.sort_values([ROUTE_COL, DATE_COL]).reset_index(drop=True)


def train_test_forecast(
    route_df: pd.DataFrame,
    config: ForecastConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Fit Prophet on one route and evaluate on the latest holdout months."""
    if len(route_df) <= config.test_months:
        raise ValueError("not enough rows for train/test split")

    train_df = route_df.iloc[: -config.test_months]
    test_df = route_df.iloc[-config.test_months :]
    model = _fit_prophet(train_df, config.target_col)

    test_future = test_df[[DATE_COL]].rename(columns={DATE_COL: "ds"})
    test_pred = model.predict(test_future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    actual = test_df[config.target_col].to_numpy()
    predicted = test_pred["yhat"].to_numpy()
    comparison = test_df[[DATE_COL, ROUTE_COL, config.target_col]].copy()
    comparison = comparison.rename(columns={config.target_col: "actual"})
    comparison["predicted"] = predicted
    comparison["error"] = comparison["actual"] - comparison["predicted"]
    comparison["abs_error"] = comparison["error"].abs()

    metrics = {
        "rows": float(len(route_df)),
        "train_rows": float(len(train_df)),
        "test_rows": float(len(test_df)),
        "mae_pp": _mae(actual, predicted),
        "rmse_pp": _rmse(actual, predicted),
        "mean_error_pp": float(np.mean(actual - predicted)),
    }

    final_model = _fit_prophet(route_df, config.target_col)
    future = final_model.make_future_dataframe(
        periods=config.horizon_months,
        freq="MS",
        include_history=True,
    )
    forecast = final_model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    return forecast, comparison, metrics


def run_forecast(
    df: pd.DataFrame,
    config: ForecastConfig = ForecastConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run route-level Prophet forecasts and return forecast/metric tables."""
    missing = {DATE_COL, ROUTE_COL, config.target_col} - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    forecast_frames = []
    comparison_frames = []
    metric_rows = []
    for route_name, route_df in df.groupby(ROUTE_COL, sort=True):
        route_df = (
            route_df[[DATE_COL, ROUTE_COL, config.target_col]]
            .dropna(subset=[config.target_col])
            .sort_values(DATE_COL)
            .copy()
        )
        forecast, comparison, metrics = train_test_forecast(route_df, config)
        forecast.insert(0, ROUTE_COL, route_name)
        forecast["target"] = config.target_col
        forecast_frames.append(forecast)
        comparison["target"] = config.target_col
        comparison_frames.append(comparison)

        metrics.update({ROUTE_COL: route_name, "target": config.target_col})
        metric_rows.append(metrics)

    forecasts = pd.concat(forecast_frames, ignore_index=True)
    comparisons = pd.concat(comparison_frames, ignore_index=True)
    metrics_df = pd.DataFrame(metric_rows)[
        [
            ROUTE_COL,
            "target",
            "rows",
            "train_rows",
            "test_rows",
            "mae_pp",
            "rmse_pp",
            "mean_error_pp",
        ]
    ]
    return forecasts, comparisons, metrics_df


def save_outputs(
    forecasts: pd.DataFrame,
    comparisons: pd.DataFrame,
    metrics: pd.DataFrame,
    forecast_path: Path = FORECAST_PATH,
    comparison_path: Path = COMPARISON_PATH,
    metrics_path: Path = METRICS_PATH,
) -> None:
    forecast_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(forecast_path, index=False, encoding="utf-8-sig")
    comparisons.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")


def save_forecast_plot(
    forecasts: pd.DataFrame,
    source_df: pd.DataFrame,
    target_col: str,
    output_path: Path = IMG_DIR / "part4_prophet_forecast.png",
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    plt.rcParams["axes.unicode_minus"] = False
    for font in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
        plt.rcParams["font.family"] = font
        break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=False)
    axes_flat = axes.flatten()
    for ax, route_name in zip(axes_flat, sorted(forecasts[ROUTE_COL].unique()), strict=False):
        actual = source_df[source_df[ROUTE_COL] == route_name].sort_values(DATE_COL)
        pred = forecasts[forecasts[ROUTE_COL] == route_name].sort_values("ds")
        ax.plot(actual[DATE_COL], actual[target_col], label="actual", color="#1f77b4")
        ax.plot(pred["ds"], pred["yhat"], label="forecast", color="#d62728")
        ax.fill_between(
            pred["ds"],
            pred["yhat_lower"],
            pred["yhat_upper"],
            color="#d62728",
            alpha=0.15,
        )
        ax.set_title(route_name)
        ax.grid(alpha=0.25)
    for ax in axes_flat[len(forecasts[ROUTE_COL].unique()) :]:
        ax.axis("off")
    axes_flat[0].legend()
    fig.suptitle(f"Part 4 Prophet Forecast: {target_col}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _fit_prophet(df: pd.DataFrame, target_col: str):
    try:
        from prophet import Prophet
    except ImportError as exc:
        raise ImportError(
            "prophet is required for Part 4. Install project requirements first."
        ) from exc

    prophet_df = df[[DATE_COL, target_col]].rename(columns={DATE_COL: "ds", target_col: "y"})
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
    )
    model.fit(prophet_df)
    return model


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def main() -> None:
    config = ForecastConfig()
    df = load_model_input()
    forecasts, comparisons, metrics = run_forecast(df, config)
    save_outputs(forecasts, comparisons, metrics)
    save_forecast_plot(forecasts, df, config.target_col)

    print(f"target: {config.target_col}")
    print(f"saved: {FORECAST_PATH}")
    print(f"saved: {COMPARISON_PATH}")
    print(f"saved: {METRICS_PATH}")
    print(metrics.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
