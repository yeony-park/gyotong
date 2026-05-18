"""
공휴일 데이터 수집 · 전처리 · EDA
──────────────────────────────────
1. 한국천문연구원 특일 정보 API로 2004~2024년 공휴일 수집
2. 월별 집계 → ktx_long.csv 조인
3. 공휴일 관련 EDA (상관분석, 명절 전후 비교, 황금연휴 효과)
4. 파생변수 생성 → ktx_long.csv 재저장

실행 전 확인:
  - API_KEY: 발급받은 서비스키 (디코딩된 키) 입력
  - 파일 경로: 프로젝트 루트에서 실행 가정
"""

import os
import time
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from pathlib import Path

# ── 설정 ───────────────────────────────────────────
API_KEY   = os.environ.get("HOLIDAY_API_KEY", "여기에_디코딩된_서비스키_입력")
BASE_URL  = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
DATA_DIR  = Path("data/processed")
EDA_DIR   = DATA_DIR / "eda_results"
EDA_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR   = Path("outputs/img")
IMG_DIR.mkdir(parents=True, exist_ok=True)

# 명절 이름 목록 (설날·추석 연휴)
FESTIVAL_NAMES = {"설날", "추석", "대체공휴일"}


def write_image_or_skip(fig, path: Path) -> None:
    """Save Plotly image when Kaleido is available; keep data outputs otherwise."""
    try:
        fig.write_image(str(path))
        print(f"✅ {path.name} 저장")
    except ValueError as exc:
        if "kaleido" not in str(exc).lower():
            raise
        print(f"⚠️  {path.name} 저장 건너뜀: kaleido 미설치")


# ══════════════════════════════════════════════════
# 1. 공휴일 데이터 수집
# ══════════════════════════════════════════════════

def fetch_holidays_one_year(year: int) -> list[dict]:
    """
    API 호출 → 해당 연도 전체 공휴일 리스트 반환
    solMonth 없이 solYear만 넣으면 연간 전체 데이터가 옴
    → 월별 호출(12회) 대신 연도별 1회 호출로 효율화
    """
    params = {
        "ServiceKey": API_KEY,
        "solYear":    year,
        "numOfRows":  100,    # 연간 공휴일 최대 ~30개, 여유있게 100
        "_type":      "json",
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        body  = data["response"]["body"]
        items = body.get("items", "")

        # 공휴일이 없는 연도 (빈 응답)
        if not items or items == "":
            return []

        item = items["item"]
        # 단일 항목이면 dict, 복수면 list
        result = item if isinstance(item, list) else [item]

        # totalCount > numOfRows 이면 데이터 누락 가능 → 경고
        total = int(body.get("totalCount", 0))
        if total > 100:
            print(f"  ⚠️  {year}년 totalCount={total} > numOfRows=100 → numOfRows 증가 필요")

        return result

    except Exception as e:
        print(f"  ⚠️  {year}년 수집 실패: {e}")
        return []


def fetch_all_holidays(start_year: int = 2004,
                       end_year:   int = 2024) -> pd.DataFrame:
    """
    start_year~end_year 전체 공휴일 수집
    연도별 1회 호출 → 총 21회 (기존 월별 252회 대비 대폭 감소)
    """
    records = []
    total = end_year - start_year + 1

    for i, year in enumerate(range(start_year, end_year + 1), 1):
        items = fetch_holidays_one_year(year)
        for item in items:
            records.append({
                "date":       pd.to_datetime(str(item["locdate"]), format="%Y%m%d"),
                "name":       item["dateName"],
                "is_holiday": item["isHoliday"] == "Y",
                "date_kind":  item.get("dateKind", ""),
            })
        print(f"  [{i:02d}/{total}] {year}년: {len(items)}건 수집")
        time.sleep(0.1)   # API 부하 방지 (연도별이라 여유있게)

    if not records:
        raise RuntimeError("수집된 공휴일 데이터가 없습니다. API_KEY를 확인하세요.")

    df = pd.DataFrame(records)
    df["year"]      = df["date"].dt.year
    df["month"]     = df["date"].dt.month
    df["yearmonth"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df


# ══════════════════════════════════════════════════
# 2. 월별 파생변수 생성
# ══════════════════════════════════════════════════

def make_monthly_features(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    일별 공휴일 → 월별 집계 파생변수 생성

    컬럼 설명:
      공휴일수       : 해당 월의 법정 공휴일 개수 (isHoliday=Y)
      명절연휴포함   : 설날 또는 추석 연휴가 포함된 달 (0/1)
      황금연휴포함   : 5일 이상 연속 공휴일 포함 (0/1) — 주말 포함 계산
      설날달         : 설날이 포함된 달 (0/1)
      추석달         : 추석이 포함된 달 (0/1)
      명절전달       : 설날·추석 전월 (0/1)
      명절후달       : 설날·추석 다음달 (0/1)
    """
    # ── 기본 집계 ──
    monthly = (
        df_raw[df_raw["is_holiday"]]
        .groupby("yearmonth")
        .size()
        .reset_index(name="공휴일수")
    )

    # ── 명절 포함 여부 ──
    festival_days = df_raw[df_raw["name"].isin(FESTIVAL_NAMES)]
    seollal_months = set(
        festival_days[festival_days["name"] == "설날"]["yearmonth"]
    )
    chuseok_months = set(
        festival_days[festival_days["name"] == "추석"]["yearmonth"]
    )

    monthly["설날달"] = monthly["yearmonth"].isin(seollal_months).astype(int)
    monthly["추석달"] = monthly["yearmonth"].isin(chuseok_months).astype(int)
    monthly["명절연휴포함"] = (
        (monthly["설날달"] == 1) | (monthly["추석달"] == 1)
    ).astype(int)

    # ── 명절 전달·후달 ──
    festival_months = seollal_months | chuseok_months
    monthly["명절전달"] = monthly["yearmonth"].apply(
        lambda ym: int(
            (ym + pd.DateOffset(months=1)) in festival_months
        )
    )
    monthly["명절후달"] = monthly["yearmonth"].apply(
        lambda ym: int(
            (ym - pd.DateOffset(months=1)) in festival_months
        )
    )

    # ── 황금연휴 (5일 이상 연속 휴일, 주말 포함) ──
    all_dates = pd.date_range("2004-01-01", "2024-12-31")
    holiday_set = set(df_raw[df_raw["is_holiday"]]["date"].dt.normalize())
    weekend_set = set(all_dates[all_dates.weekday >= 5])
    off_set = holiday_set | weekend_set

    # 연속 구간 탐색
    golden_months = set()
    sorted_dates = sorted(off_set)
    streak, streak_start = 1, sorted_dates[0]
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
            streak += 1
        else:
            if streak >= 5:
                golden_months.add(
                    streak_start.to_period("M").to_timestamp()
                )
            streak, streak_start = 1, sorted_dates[i]

    monthly["황금연휴포함"] = monthly["yearmonth"].isin(golden_months).astype(int)

    # 결측 월(공휴일 0개)도 포함되도록 전체 월 인덱스와 merge
    all_months = pd.DataFrame({
        "yearmonth": pd.date_range("2004-01-01", "2024-12-31", freq="MS")
    })
    monthly = all_months.merge(monthly, on="yearmonth", how="left").fillna(0)
    for col in ["공휴일수", "설날달", "추석달", "명절연휴포함",
                "명절전달", "명절후달", "황금연휴포함"]:
        monthly[col] = monthly[col].astype(int)

    return monthly


# ══════════════════════════════════════════════════
# 3. ktx_long.csv에 조인
# ══════════════════════════════════════════════════

def join_to_ktx(monthly: pd.DataFrame) -> pd.DataFrame:
    """ktx_long.csv + 공휴일 월별 변수 조인"""
    ktx = pd.read_csv(DATA_DIR / "ktx_long.csv", parse_dates=["yearmonth"])
    holiday_feature_cols = [
        "공휴일수",
        "설날달",
        "추석달",
        "명절연휴포함",
        "명절전달",
        "명절후달",
        "황금연휴포함",
    ]
    ktx = ktx.drop(columns=holiday_feature_cols, errors="ignore")
    merged = ktx.merge(monthly, on="yearmonth", how="left")

    # 혹시 남은 NaN → 0 처리
    for col in holiday_feature_cols:
        merged[col] = merged[col].fillna(0).astype(int)

    merged.to_csv(DATA_DIR / "ktx_long.csv", index=False)
    print(f"✅ ktx_long.csv 업데이트 완료: {merged.shape}")
    return merged


# ══════════════════════════════════════════════════
# 4. EDA
# ══════════════════════════════════════════════════

def eda_holiday(df: pd.DataFrame) -> None:
    """공휴일 관련 EDA 시각화 + 통계 검정"""

    # ── 4-1. 공휴일수 vs 공실률 상관분석 ──
    print("\n=== 공휴일수 vs 공실률 Spearman 상관계수 ===")
    for 노선 in df["노선"].unique():
        sub = df[df["노선"] == 노선].dropna(subset=["공실률", "공휴일수"])
        r, p = stats.spearmanr(sub["공휴일수"], sub["공실률"])
        sig = "✅ 유의미" if p < 0.05 else "❌ 유의미하지 않음"
        print(f"  {노선}: r={r:.3f}, p={p:.4f} → {sig}")

    # ── 4-2. 명절 포함 달 vs 비명절 달 공실률 비교 ──
    print("\n=== 명절 포함 달 vs 비명절 달 공실률 (Mann-Whitney) ===")
    results = []
    for 노선 in df["노선"].unique():
        sub = df[df["노선"] == 노선].dropna(subset=["공실률"])
        festival = sub[sub["명절연휴포함"] == 1]["공실률"]
        non_fst  = sub[sub["명절연휴포함"] == 0]["공실률"]
        stat, p  = stats.mannwhitneyu(festival, non_fst, alternative="two-sided")
        diff     = festival.mean() - non_fst.mean()
        sig = "✅" if p < 0.05 else "❌"
        print(f"  {노선}: 명절달 평균 {festival.mean():.1f}% vs "
              f"비명절달 {non_fst.mean():.1f}% | 차이 {diff:+.1f}%p | p={p:.4f} {sig}")
        results.append({
            "노선": 노선,
            "명절달_평균공실률": round(festival.mean(), 1),
            "비명절달_평균공실률": round(non_fst.mean(), 1),
            "차이_pct": round(diff, 1),
            "p_value": round(p, 4),
            "유의미": p < 0.05,
        })
    pd.DataFrame(results).to_csv(
        EDA_DIR / "holiday_mannwhitney.csv", index=False
    )

    # ── 4-3. Boxplot: 명절달 vs 비명절달 ──
    df_plot = df.copy()
    df_plot["명절여부"] = df_plot["명절연휴포함"].map({1: "명절 포함 달", 0: "비명절 달"})
    fig = px.box(
        df_plot, x="명절여부", y="공실률", color="명절여부",
        facet_col="노선", facet_col_wrap=3,
        title="명절 포함 달 vs 비명절 달 공실률 비교",
        color_discrete_map={"명절 포함 달": "#E74C3C", "비명절 달": "#3498DB"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(height=600)
    write_image_or_skip(fig, IMG_DIR / "boxplot_holiday_festival.png")

    # ── 4-4. 명절 전/중/후 공실률 패턴 Line chart ──
    df["명절시점"] = "일반"
    df.loc[df["명절전달"]    == 1, "명절시점"] = "명절 전달"
    df.loc[df["명절연휴포함"] == 1, "명절시점"] = "명절 당월"
    df.loc[df["명절후달"]    == 1, "명절시점"] = "명절 후달"

    pattern = (
        df.groupby(["노선", "명절시점"])["공실률"]
        .mean().reset_index()
    )
    cat_order = ["명절 전달", "명절 당월", "명절 후달", "일반"]
    fig2 = px.bar(
        pattern,
        x="명절시점", y="공실률", color="노선",
        barmode="group",
        category_orders={"명절시점": cat_order},
        title="명절 전·중·후 평균 공실률 비교 (노선별)",
        labels={"공실률": "평균 공실률 (%)"},
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    write_image_or_skip(fig2, IMG_DIR / "barplot_holiday_timing.png")

    # ── 4-5. 황금연휴 효과 ──
    print("\n=== 황금연휴 포함 달 vs 일반 달 공실률 ===")
    for 노선 in df["노선"].unique():
        sub    = df[df["노선"] == 노선].dropna(subset=["공실률"])
        golden = sub[sub["황금연휴포함"] == 1]["공실률"]
        normal = sub[sub["황금연휴포함"] == 0]["공실률"]
        if len(golden) == 0:
            continue
        diff = golden.mean() - normal.mean()
        print(f"  {노선}: 황금연휴 {golden.mean():.1f}% vs "
              f"일반 {normal.mean():.1f}% | 차이 {diff:+.1f}%p")

    # ── 4-6. 공휴일수별 평균 공실률 Line chart ──
    hol_trend = (
        df.groupby(["공휴일수", "노선"])["공실률"]
        .mean().reset_index()
    )
    fig3 = px.line(
        hol_trend, x="공휴일수", y="공실률", color="노선",
        markers=True,
        title="월별 공휴일 수에 따른 평균 공실률",
        labels={"공휴일수": "공휴일 수 (일/월)", "공실률": "평균 공실률 (%)"},
    )
    fig3.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    write_image_or_skip(fig3, IMG_DIR / "line_holiday_count.png")


# ══════════════════════════════════════════════════
# 5. ktx_model_input.csv 업데이트 (feature 추가)
# ══════════════════════════════════════════════════

def update_model_input() -> None:
    """
    ktx_model_input.csv에 공휴일 파생변수 추가
    feature_cols 확장:
      기존 + ['공휴일수', '명절연휴포함', '황금연휴포함']
    """
    ktx_long  = pd.read_csv(DATA_DIR / "ktx_long.csv",
                             parse_dates=["yearmonth"])
    model_in  = pd.read_csv(DATA_DIR / "ktx_model_input.csv",
                             parse_dates=["yearmonth"])

    holiday_cols = ["yearmonth", "노선", "공휴일수",
                    "명절연휴포함", "황금연휴포함", "명절전달", "명절후달"]

    # ktx_long에서 공휴일 컬럼만 추출하여 조인
    holiday_sub = ktx_long[holiday_cols]
    model_in = model_in.drop(
        columns=["공휴일수", "명절연휴포함", "황금연휴포함", "명절전달", "명절후달"],
        errors="ignore",
    )
    model_in = model_in.merge(holiday_sub, on=["yearmonth", "노선"], how="left")

    # 결측 처리
    for col in ["공휴일수", "명절연휴포함", "황금연휴포함", "명절전달", "명절후달"]:
        model_in[col] = model_in[col].fillna(0).astype(int)

    model_in.to_csv(DATA_DIR / "ktx_model_input.csv", index=False)
    print(f"✅ ktx_model_input.csv 업데이트 완료: {model_in.shape}")
    print("추가된 feature: 공휴일수, 명절연휴포함, 황금연휴포함, 명절전달, 명절후달")


# ══════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════

def main():
    holiday_csv = DATA_DIR / "holidays_raw.csv"

    # 1. 공휴일 수집 (이미 있으면 스킵)
    if holiday_csv.exists():
        print("✅ 기존 공휴일 데이터 로드")
        df_raw = pd.read_csv(holiday_csv, parse_dates=["date", "yearmonth"])
    else:
        print("📡 공휴일 API 수집 시작 (약 2~3분 소요)...")
        df_raw = fetch_all_holidays(2004, 2024)
        df_raw.to_csv(holiday_csv, index=False)
        print(f"✅ 수집 완료: {len(df_raw)}건 → {holiday_csv}")

    # 2. 월별 파생변수 생성
    print("\n📊 월별 파생변수 생성...")
    monthly = make_monthly_features(df_raw)
    print(f"  공휴일 월별 집계: {monthly.shape}")
    print(monthly[["yearmonth","공휴일수","명절연휴포함","황금연휴포함"]].head(10).to_string(index=False))

    # 3. ktx_long.csv 조인
    print("\n🔗 ktx_long.csv 조인...")
    df_merged = join_to_ktx(monthly)

    # 4. EDA
    print("\n📈 EDA 시작...")
    eda_holiday(df_merged)

    # 5. 모델 input 업데이트
    print("\n🔄 ktx_model_input.csv 업데이트...")
    update_model_input()

    print("\n✅ 전체 완료")
    print("생성된 파일:")
    print(f"  data/processed/holidays_raw.csv")
    print(f"  data/processed/ktx_long.csv (공휴일 컬럼 추가)")
    print(f"  data/processed/ktx_model_input.csv (feature 추가)")
    print(f"  outputs/img/boxplot_holiday_festival.png")
    print(f"  outputs/img/barplot_holiday_timing.png")
    print(f"  outputs/img/line_holiday_count.png")
    print(f"  data/processed/eda_results/holiday_mannwhitney.csv")


if __name__ == "__main__":
    main()
