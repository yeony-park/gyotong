"""Part 1: route and station aggregation datasets."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PASSENGER_FILE = RAW_DIR / "station_boarding_alighting_20241231.csv"
KTX_SECTION_FILE = RAW_DIR / "ktx_section_stats_20240101.xlsx"


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def load_station_passengers(path: Path = PASSENGER_FILE) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    df = df.rename(
        columns={
            "역명": "station_name",
            "단위": "unit",
            "승차인원": "boarding_count",
            "하차인원": "alighting_count",
        }
    )
    df["boarding_count"] = _number(df["boarding_count"]).fillna(0).astype("int64")
    df["alighting_count"] = _number(df["alighting_count"]).fillna(0).astype("int64")
    df["total_count"] = df["boarding_count"] + df["alighting_count"]
    df["source_date"] = _date_from_filename(path.name)
    return df[
        [
            "source_date",
            "station_name",
            "unit",
            "boarding_count",
            "alighting_count",
            "total_count",
        ]
    ].sort_values("boarding_count", ascending=False)


def build_station_summary(station_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        station_df.groupby("station_name", as_index=False)
        .agg(
            boarding_count=("boarding_count", "sum"),
            alighting_count=("alighting_count", "sum"),
            total_count=("total_count", "sum"),
        )
        .sort_values("boarding_count", ascending=False)
    )
    total_boarding = summary["boarding_count"].sum()
    summary["boarding_share"] = summary["boarding_count"] / total_boarding
    return summary


def load_ktx_section_stats(path: Path = KTX_SECTION_FILE) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    sections = [
        ("service_count_weekday", "count", 3, 4, 5),
        ("service_count_weekend", "count", 9, 10, 11),
        ("fare", "krw", 16, 17, 19),
        ("passengers", "thousand_people", 23, 24, 26),
    ]

    frames: list[pd.DataFrame] = []
    for metric, unit, header_row, start_row, end_row in sections:
        headers = raw.iloc[header_row].tolist()
        chunk = raw.iloc[start_row:end_row].copy()
        chunk.columns = headers
        chunk = chunk.rename(columns={"구분": "section_name"})
        chunk = chunk.dropna(subset=["section_name"])
        value_columns = [
            col for col in chunk.columns if col != "section_name" and pd.notna(col)
        ]
        long_df = chunk.melt(
            id_vars=["section_name"],
            value_vars=value_columns,
            var_name="year",
            value_name="value",
        )
        long_df["metric"] = metric
        long_df["unit"] = unit
        long_df["route_name"] = long_df["section_name"].map(_route_name)
        long_df["year"] = long_df["year"].map(_year_value)
        long_df["value"] = _number(long_df["value"])
        frames.append(long_df.dropna(subset=["year", "value"]))

    result = pd.concat(frames, ignore_index=True)
    result["year"] = result["year"].astype("int64")
    return result[["metric", "unit", "route_name", "section_name", "year", "value"]]


def build_route_summary(ktx_stats: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    selected_year = year or int(ktx_stats["year"].max())
    route = ktx_stats[ktx_stats["year"] == selected_year].copy()
    route = route.pivot_table(
        index=["route_name", "year"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()
    route.columns.name = None
    return route.sort_values("route_name")


def _date_from_filename(name: str) -> str | None:
    match = re.search(r"(20\d{6})", name)
    if not match:
        return None
    value = match.group(1)
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _year_value(value: object) -> int | None:
    if pd.isna(value):
        return None
    match = re.search(r"(20\d{2})", str(value))
    return int(match.group(1)) if match else None


def _route_name(value: object) -> str:
    text = str(value).strip()
    return text.split("(", 1)[0]


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    station_passengers = load_station_passengers()
    station_summary = build_station_summary(station_passengers)
    ktx_stats = load_ktx_section_stats()
    route_summary = build_route_summary(ktx_stats)

    outputs = {
        "station_passengers_standard.csv": station_passengers,
        "station_summary.csv": station_summary,
        "ktx_route_stats_long.csv": ktx_stats,
        "route_summary.csv": route_summary,
    }
    for filename, df in outputs.items():
        path = PROCESSED_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(path)


if __name__ == "__main__":
    main()
