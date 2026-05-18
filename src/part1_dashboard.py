"""Streamlit dashboard for Part 1 route and station aggregation."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT_DIR / ".matplotlib"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


DATA_DIR = ROOT_DIR / "data" / "processed"
STATION_SUMMARY = DATA_DIR / "station_summary.csv"
ROUTE_STATIONS = DATA_DIR / "ktx_route_stations_standard.csv"
ROUTE_SUMMARY = DATA_DIR / "route_summary.csv"


def setup_plot_font() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    for font in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
        plt.rcParams["font.family"] = font
        break


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    station = pd.read_csv(STATION_SUMMARY)
    route_stations = pd.read_csv(ROUTE_STATIONS)
    route_summary = pd.read_csv(ROUTE_SUMMARY)
    station_route = route_stations.merge(station, on="station_name", how="left")
    station_route[["boarding_count", "alighting_count", "total_count"]] = station_route[
        ["boarding_count", "alighting_count", "total_count"]
    ].fillna(0)
    return station, station_route, route_summary


def format_count(value: float | int) -> str:
    return f"{int(value):,}"


def plot_top_stations(station: pd.DataFrame, top_n: int, title_suffix: str = "") -> None:
    top = station.nlargest(top_n, "boarding_count").sort_values("boarding_count")
    fig, ax = plt.subplots(figsize=(9, max(4, top_n * 0.35)))
    ax.barh(top["station_name"], top["boarding_count"], color="#d62728")
    ax.set_title(f"승차 인원 상위 {top_n}개 역{title_suffix}")
    ax.set_xlabel("승차 인원")
    ax.grid(axis="x", alpha=0.25)
    for i, value in enumerate(top["boarding_count"]):
        ax.text(value, i, f" {format_count(value)}", va="center", fontsize=8)
    st.pyplot(fig, clear_figure=True)


def plot_boarding_vs_alighting(station: pd.DataFrame, top_n: int, title_suffix: str = "") -> None:
    top = station.nlargest(top_n, "total_count").sort_values("total_count")
    fig, ax = plt.subplots(figsize=(9, max(4, top_n * 0.35)))
    ax.barh(top["station_name"], top["boarding_count"], label="승차", color="#1f77b4")
    ax.barh(
        top["station_name"],
        top["alighting_count"],
        left=top["boarding_count"],
        label="하차",
        color="#ff7f0e",
    )
    ax.set_title(f"총 이용 인원 상위 {top_n}개 역{title_suffix}")
    ax.set_xlabel("인원")
    ax.legend()
    ax.grid(axis="x", alpha=0.25)
    st.pyplot(fig, clear_figure=True)


def plot_route_station_counts(station_route: pd.DataFrame) -> None:
    counts = (
        station_route.groupby("line_name", as_index=False)["station_name"]
        .nunique()
        .sort_values("station_name")
    )
    fig, ax = plt.subplots(figsize=(8, max(3.5, len(counts) * 0.35)))
    ax.barh(counts["line_name"], counts["station_name"], color="#2ca02c")
    ax.set_title("노선별 등록 역 수")
    ax.set_xlabel("역 수")
    ax.grid(axis="x", alpha=0.25)
    for i, value in enumerate(counts["station_name"]):
        ax.text(value, i, f" {int(value)}", va="center", fontsize=8)
    st.pyplot(fig, clear_figure=True)


def plot_route_stations(station_route: pd.DataFrame, line_name: str) -> None:
    selected = station_route[station_route["line_name"] == line_name].copy()
    selected = selected.sort_values("station_order")
    fig, ax = plt.subplots(figsize=(10, max(4, len(selected) * 0.3)))
    ax.barh(selected["station_name"], selected["boarding_count"], color="#9467bd")
    ax.invert_yaxis()
    ax.set_title(f"{line_name} 정차역 순서별 승차 인원")
    ax.set_xlabel("승차 인원")
    ax.grid(axis="x", alpha=0.25)
    st.pyplot(fig, clear_figure=True)


def plot_route_summary(route_summary: pd.DataFrame) -> None:
    if route_summary.empty:
        st.info("노선 요약 데이터가 없습니다.")
        return
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    x = range(len(route_summary))
    ax1.bar(x, route_summary["passengers"], color="#17becf", label="이용객(천명)")
    ax1.set_ylabel("이용객(천명)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(route_summary["route_name"])
    ax1.grid(axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(
        list(x),
        route_summary["service_count_weekday"],
        color="#d62728",
        marker="o",
        label="주중 운행횟수",
    )
    ax2.set_ylabel("운행횟수")
    ax1.set_title("2023년 노선별 KTX 이용객 및 주중 운행횟수")
    st.pyplot(fig, clear_figure=True)


def main() -> None:
    setup_plot_font()
    st.set_page_config(page_title="파트 1 KTX 집계", layout="wide")
    st.title("파트 1: KTX 노선·역별 집계")

    missing = [path for path in [STATION_SUMMARY, ROUTE_STATIONS, ROUTE_SUMMARY] if not path.exists()]
    if missing:
        st.error("필요한 processed 파일이 없습니다.")
        for path in missing:
            st.code(str(path))
        st.stop()

    station, station_route, route_summary = load_data()

    top_n = st.sidebar.slider("Top N 역", min_value=5, max_value=30, value=15, step=5)
    line_names = sorted(station_route["line_name"].dropna().unique())
    selected_line = st.sidebar.selectbox("노선 선택", ["전체"] + line_names)

    if selected_line == "전체":
        view_station = station.copy()
        view_route_station = station_route.copy()
        title_suffix = ""
    else:
        view_route_station = station_route[station_route["line_name"] == selected_line].copy()
        view_station = (
            view_route_station[
                ["station_name", "boarding_count", "alighting_count", "total_count"]
            ]
            .drop_duplicates("station_name")
            .sort_values("boarding_count", ascending=False)
        )
        title_suffix = f" ({selected_line})"

    total_boarding = view_station["boarding_count"].sum()
    total_alighting = view_station["alighting_count"].sum()
    station_count = view_station["station_name"].nunique()
    route_count = view_route_station["line_name"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("선택 역 수", format_count(station_count))
    col2.metric("선택 노선 수", format_count(route_count))
    col3.metric("선택 승차 인원", format_count(total_boarding))
    col4.metric("선택 하차 인원", format_count(total_alighting))

    tab1, tab2, tab3 = st.tabs(["역별 집계", "노선별 역정보", "원본 테이블"])

    with tab1:
        left, right = st.columns(2)
        with left:
            plot_top_stations(view_station, top_n, title_suffix)
        with right:
            plot_boarding_vs_alighting(view_station, top_n, title_suffix)

    with tab2:
        left, right = st.columns(2)
        with left:
            plot_route_station_counts(view_route_station)
        with right:
            route_summary_view = (
                route_summary
                if selected_line == "전체"
                else route_summary[route_summary["route_name"] == selected_line]
            )
            plot_route_summary(route_summary_view)
        if selected_line == "전체":
            st.info("정차역 순서별 차트를 보려면 왼쪽에서 특정 노선을 선택하세요.")
        else:
            plot_route_stations(station_route, selected_line)
        st.dataframe(
            view_route_station[
                [
                    "line_name",
                    "station_order",
                    "station_name",
                    "address",
                    "boarding_count",
                    "alighting_count",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        st.subheader("station_summary.csv")
        st.dataframe(station, use_container_width=True, hide_index=True)
        st.subheader("ktx_route_stations_standard.csv + station_summary.csv")
        st.dataframe(station_route, use_container_width=True, hide_index=True)
        st.subheader("route_summary.csv")
        st.dataframe(route_summary, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
