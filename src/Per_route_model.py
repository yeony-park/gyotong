"""
노선별 개별 CatBoost 모델 학습 및 통합 모델과 성능 비교
──────────────────────────────────────────────────────
1. 노선별 개별 모델 학습 (Walk-forward CV)
2. 통합 모델 MAE vs 개별 모델 MAE 비교
3. 노선별 모델 저장
4. SHAP 노선별 변수 중요도 비교

실행 위치: 프로젝트 루트
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from catboost import CatBoostRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import shap
from pathlib import Path

# ── 설정 ───────────────────────────────────────────
DATA_DIR  = Path("data/processed")
MODEL_DIR = Path("models")
EDA_DIR   = DATA_DIR / "eda_results"
IMG_DIR   = Path("outputs/img")
MODEL_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)

# feature 목록 (공휴일 변수 포함 버전)
# 공휴일 변수가 없으면 아래 BASE_FEATURES만 사용
BASE_FEATURES = [
    "월", "분기", "계절", "코로나기간", "SRT개통후",
    "공실률_lag1", "공실률_lag12", "공실률_ma3",
]
HOLIDAY_FEATURES = [
    "공휴일수", "명절연휴포함", "황금연휴포함",
]
TARGET = "공실률"
CAT_FEATURES_BASE    = ["계절"]          # 노선별 모델: 노선 변수 제거
CAT_FEATURES_UNIFIED = ["노선", "계절"]  # 통합 모델용

ROUTES = ["경부선", "호남선", "경전선", "전라선", "동해선"]

# 노선별 fold 수 (데이터 적은 노선은 축소)
FOLD_MAP = {
    "경부선": 5,
    "호남선": 5,
    "경전선": 4,
    "전라선": 4,
    "동해선": 3,   # 105행으로 가장 적음
}

CATBOOST_PARAMS = dict(
    iterations=500,
    learning_rate=0.05,
    depth=6,
    eval_metric="MAE",
    early_stopping_rounds=50,
    random_seed=42,
    verbose=False,
)


# ══════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════

def get_features(df: pd.DataFrame, include_holiday: bool = True) -> list[str]:
    """사용 가능한 feature 목록 반환"""
    features = BASE_FEATURES.copy()
    if include_holiday:
        available = [f for f in HOLIDAY_FEATURES if f in df.columns]
        features += available
    return features


def walk_forward_cv(df: pd.DataFrame,
                    features: list[str],
                    cat_features: list[str],
                    n_splits: int) -> dict:
    """Walk-forward CV → fold별 MAE·RMSE 반환"""
    df = df.sort_values("yearmonth").reset_index(drop=True)
    X  = df[features]
    y  = df[TARGET]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    maes, rmses = [], []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

        cat_idx = [X_tr.columns.get_loc(c) for c in cat_features if c in X_tr.columns]
        model = CatBoostRegressor(**CATBOOST_PARAMS)
        model.fit(X_tr, y_tr,
                  cat_features=cat_idx,
                  eval_set=(X_te, y_te),
                  use_best_model=True)

        pred = model.predict(X_te)
        mae  = mean_absolute_error(y_te, pred)
        rmse = np.sqrt(mean_squared_error(y_te, pred))
        maes.append(mae)
        rmses.append(rmse)
        print(f"    fold {fold}: MAE={mae:.4f}, RMSE={rmse:.4f}")

    return {"mae_list": maes, "rmse_list": rmses,
            "mean_mae": np.mean(maes), "mean_rmse": np.mean(rmses)}


# ══════════════════════════════════════════════════
# 1. 노선별 개별 모델 학습
# ══════════════════════════════════════════════════

def train_per_route(df: pd.DataFrame,
                    include_holiday: bool = True) -> dict:
    """
    노선별 개별 모델 학습
    반환: {노선명: {"cv": cv_result, "model": 학습모델}}
    """
    features = get_features(df, include_holiday)
    results  = {}

    for 노선 in ROUTES:
        print(f"\n── {노선} ──")
        sub = df[df["노선"] == 노선].copy().dropna(subset=features + [TARGET])
        sub = sub.sort_values("yearmonth").reset_index(drop=True)
        print(f"  데이터 {len(sub)}행")

        n_splits = FOLD_MAP[노선]
        cv = walk_forward_cv(sub, features, CAT_FEATURES_BASE, n_splits)
        print(f"  평균 MAE={cv['mean_mae']:.4f}, RMSE={cv['mean_rmse']:.4f}")

        # 전체 데이터로 최종 모델 학습
        X  = sub[features]
        y  = sub[TARGET]
        cat_idx = [X.columns.get_loc(c) for c in CAT_FEATURES_BASE if c in X.columns]
        final_model = CatBoostRegressor(**CATBOOST_PARAMS)
        final_model.fit(X, y, cat_features=cat_idx)
        final_model.save_model(str(MODEL_DIR / f"catboost_{노선}.cbm"))
        print(f"  모델 저장: models/catboost_{노선}.cbm")

        results[노선] = {"cv": cv, "model": final_model,
                         "X": X, "y": y, "features": features}

    return results


# ══════════════════════════════════════════════════
# 2. 통합 모델 MAE 로드 (기존 결과)
# ══════════════════════════════════════════════════

# 기존 통합 모델 MAE (파트 3에서 확인된 수치)
UNIFIED_MAE = {
    "경부선": None,  # 노선별 분리 없이 전체 MAE만 있었음
    "호남선": None,
    "경전선": None,
    "전라선": None,
    "동해선": None,
    "전체":   6.9959,
}


# ══════════════════════════════════════════════════
# 3. 성능 비교표 생성
# ══════════════════════════════════════════════════

def make_comparison_table(per_route_results: dict) -> pd.DataFrame:
    """노선별 개별 모델 vs 통합 모델 비교표"""
    rows = []
    for 노선, res in per_route_results.items():
        rows.append({
            "노선":           노선,
            "데이터수(행)":   len(res["X"]),
            "CV_fold수":      FOLD_MAP[노선],
            "개별모델_MAE":   round(res["cv"]["mean_mae"], 4),
            "개별모델_RMSE":  round(res["cv"]["mean_rmse"], 4),
            "통합모델_MAE":   "6.9959 (전체)",
            "비고":           "개별 모델이 더 낮으면 개선",
        })
    df_cmp = pd.DataFrame(rows)
    df_cmp.to_csv(EDA_DIR / "model_comparison_per_route.csv", index=False)
    print("\n=== 노선별 성능 비교 ===")
    print(df_cmp[["노선","데이터수(행)","개별모델_MAE","개별모델_RMSE"]].to_string(index=False))
    return df_cmp


# ══════════════════════════════════════════════════
# 4. SHAP 노선별 비교
# ══════════════════════════════════════════════════

def shap_per_route(per_route_results: dict) -> None:
    """노선별 SHAP feature importance 비교 시각화"""
    shap_summary = []

    for 노선, res in per_route_results.items():
        model    = res["model"]
        X        = res["X"]
        features = res["features"]

        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        mean_shap = np.abs(shap_values).mean(axis=0)
        for feat, val in zip(features, mean_shap):
            shap_summary.append({"노선": 노선, "변수": feat, "SHAP중요도": round(val, 4)})

    df_shap = pd.DataFrame(shap_summary)
    df_shap.to_csv(EDA_DIR / "shap_per_route.csv", index=False)

    # 변수명 한국어 매핑
    name_map = {
        "공실률_lag1":   "전월 공실률",
        "공실률_ma3":    "3개월 이동평균",
        "공실률_lag12":  "전년 동월",
        "월":           "월",
        "분기":         "분기",
        "계절":         "계절",
        "코로나기간":    "코로나기간",
        "SRT개통후":     "SRT개통후",
        "공휴일수":      "공휴일수",
        "명절연휴포함":  "명절연휴포함",
        "황금연휴포함":  "황금연휴포함",
    }
    df_shap["변수_한국어"] = df_shap["변수"].map(name_map).fillna(df_shap["변수"])

    # 노선별 Top5 시각화 (pandas 3.x: apply 대신 sort+head로 그룹 키 보존)
    top5 = (
        df_shap.groupby(["노선", "변수_한국어"])["SHAP중요도"]
               .mean().reset_index()
               .sort_values("SHAP중요도", ascending=False)
               .groupby("노선", group_keys=False)
               .head(5)
               .reset_index(drop=True)
    )
    fig = px.bar(
        top5,
        x="SHAP중요도", y="변수_한국어", color="노선",
        facet_col="노선", facet_col_wrap=3,
        title="노선별 SHAP 변수 중요도 Top 5",
        height=700,
    )
    fig.update_yaxes(matches=None)
    fig.write_image(str(IMG_DIR / "shap_per_route.png"))
    print("✅ shap_per_route.png 저장")


# ══════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════

def main():
    # 데이터 로드
    print("📂 ktx_model_input.csv 로드...")
    df = pd.read_csv(DATA_DIR / "ktx_model_input.csv",
                     parse_dates=["yearmonth"])
    print(f"  shape: {df.shape}")
    print(f"  컬럼: {list(df.columns)}")

    # 공휴일 변수 있는지 확인
    has_holiday = "공휴일수" in df.columns
    print(f"  공휴일 변수 포함: {has_holiday}")

    # 1. 노선별 개별 모델 학습
    print("\n🤖 노선별 개별 CatBoost 학습 시작...")
    per_route = train_per_route(df, include_holiday=has_holiday)

    # 2. 성능 비교표
    print("\n📊 성능 비교표 생성...")
    df_cmp = make_comparison_table(per_route)

    # 3. SHAP 노선별 분석
    print("\n🔍 SHAP 노선별 분석...")
    shap_per_route(per_route)

    print("\n✅ 전체 완료")
    print("생성된 파일:")
    for 노선 in ROUTES:
        print(f"  models/catboost_{노선}.cbm")
    print(f"  data/processed/eda_results/model_comparison_per_route.csv")
    print(f"  data/processed/eda_results/shap_per_route.csv")
    print(f"  outputs/img/shap_per_route.png")

    # 4. 최종 요약
    print("\n=== 최종 요약 ===")
    print(f"통합 모델 전체 MAE: 6.9959%p")
    print("노선별 개별 모델 MAE:")
    for 노선, res in per_route.items():
        mae = res["cv"]["mean_mae"]
        print(f"  {노선}: {mae:.4f}%p")


if __name__ == "__main__":
    main()