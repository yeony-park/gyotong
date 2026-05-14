# 시각화 결과물 목록

## EDA

| 파일명 | 설명 |
|--------|------|
| `lineplot_monthly.png` | 노선별 월별 공실률 추이 (전체 기간 라인차트) |
| `trend_yearly.png` | 연도별 평균 공실률 추세 (코로나·SRT개통 구간 표시) |
| `boxplot_season.png` | 계절별 공실률 분포 박스플롯 |
| `boxplot_season_detrended.png` | 추세 제거 후 계절별 공실률 박스플롯 (순수 계절 효과 확인) |

## 공휴일 분석

| 파일명 | 설명 |
|--------|------|
| `holiday_vacancy_comparison.png` | 공휴일 포함 달 vs 비공휴일 달 평균 공실률 비교 |
| `boxplot_holiday_festival.png` | 명절 포함 달 vs 비명절 달 공실률 박스플롯 (노선별, Mann-Whitney U 검정) |
| `barplot_holiday_timing.png` | 명절 전달·당월·후달·일반달 평균 공실률 비교 막대차트 (노선별) |
| `line_holiday_count.png` | 월별 공휴일 수에 따른 평균 공실률 변화 라인차트 |
| `route_holiday_effect.png` | 노선별 공휴일 효과 크기 비교 |

## 모델 성능

| 파일명 | 설명 |
|--------|------|
| `pred_vs_actual.png` | 통합 CatBoost 모델 예측값 vs 실제값 산점도 (전체 노선) |
| `fold4_pred_vs_actual.png` | Walk-forward CV Fold 4 예측값 vs 실제값 |

## SHAP 변수 중요도

| 파일명 | 설명 |
|--------|------|
| `shap_summary.png` | 통합 모델 전체 변수 SHAP 중요도 요약 (beeswarm plot) |
| `shap_per_route.png` | 노선별 개별 모델 SHAP 변수 중요도 Top 5 비교 (facet bar chart) |
