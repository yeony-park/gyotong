"use client";

import { useEffect, useMemo, useState } from "react";

const tabs = [
  { id: "part1", label: "탭 1", name: "파트 1 노선·역 현황" },
  { id: "part2", label: "탭 2", name: "파트 2 시간·계절" },
  { id: "forecast", label: "탭 3", name: "파트 3-A/B 예측" },
  { id: "part5", label: "탭 4", name: "파트 5 외부 변수" },
];

const part1RouteOrder = ["강릉선", "경부선", "경전선", "전라선", "중부내륙선", "중앙선", "호남선"];
const vacancyRouteOrder = ["경부선", "호남선", "경전선", "전라선", "동해선"];
const forecastModes = [
  { id: "regression", code: "3-A", title: "공실률 회귀 예측", desc: "CatBoost 메인 모델" },
  { id: "timeseries", code: "3-B", title: "시계열 예측", desc: "Prophet 기준선" },
];

export default function Dashboard({ data }) {
  const [activeTab, setActiveTab] = useState("part1");
  const [forecastMode, setForecastMode] = useState("regression");
  const [selectedRoute, setSelectedRoute] = useState("전체");

  const model = useMemo(() => buildViewModel(data, selectedRoute), [data, selectedRoute]);
  const routeOptions = activeTab === "part1" ? model.part1Routes : model.vacancyRoutes;

  useEffect(() => {
    if (selectedRoute !== "전체" && !routeOptions.includes(selectedRoute)) {
      setSelectedRoute("전체");
    }
  }, [routeOptions, selectedRoute]);

  return (
    <main className="dashboard-shell">
      <section className="glass-panel rounded-[2rem]">
        <Header selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} routes={routeOptions} />
        <TabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        <section className="screen-content">
          {activeTab === "part1" && <Part1 model={model} />}
          {activeTab === "part2" && <Part2 model={model} />}
          {activeTab === "forecast" && <ForecastPanel model={model} mode={forecastMode} setMode={setForecastMode} />}
          {activeTab === "part5" && <Part5 model={model} />}
        </section>
      </section>
    </main>
  );
}

function Header({ selectedRoute, setSelectedRoute, routes }) {
  const now = new Date();
  const time = now.toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit", hour12: false });
  const date = now.toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" });

  return (
    <header className="screen-statusbar grid grid-cols-[220px_1fr_260px] items-center px-8">
      <div className="flex items-center gap-2 text-xl">
        <button type="button" className="nav-icon-button" aria-label="뒤로">‹</button>
        <button type="button" className="nav-icon-button" aria-label="홈">⌂</button>
        <button type="button" className="nav-icon-button" aria-label="메뉴">≡</button>
      </div>
      <div className="text-center">
        <div className="text-3xl font-semibold tabular-nums text-slate-700">{time}</div>
        <div className="mt-1 text-sm font-bold text-slate-500">{date}</div>
      </div>
      <label className="justify-self-end text-xs font-semibold text-slate-500">
        <span className="mb-1 block text-right">Route</span>
        <select
          value={selectedRoute}
          onChange={(event) => setSelectedRoute(event.target.value)}
          className="w-48 rounded-lg border border-slate-200 bg-white px-3 py-2 text-right text-base font-bold text-slate-700 outline-none focus:border-[#72ddb0]"
        >
          {["전체", ...routes].map((route) => (
            <option key={route} value={route}>
              {route}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}

function TabBar({ activeTab, setActiveTab }) {
  return (
    <nav className="screen-tabbar grid grid-cols-4 gap-2 px-6 py-3">
      {tabs.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={[
              "rounded-xl border px-4 py-3 text-center transition",
              active
                ? "border-[#72ddb0] bg-[#e5fbf0] text-slate-900"
                : "border-slate-200 bg-white text-slate-500 hover:border-slate-300",
            ].join(" ")}
          >
            <span className="block text-xs font-bold">{tab.label}</span>
            <span className="mt-1 block text-sm font-semibold">{tab.name}</span>
          </button>
        );
      })}
    </nav>
  );
}

function Part1({ model }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <section className="space-y-4">
        <ScreenTitle eyebrow="Electric Rail Operations" title="노선·역 현황" desc="역별 승하차와 노선 규모를 한 화면에서 확인합니다." />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Top Boarding Stations">
            <BarList rows={model.part1.topStations} labelKey="station_name" valueKey="boarding_count" color="#63dca7" />
          </Card>
          <Card title="Route Summary">
            <BarList rows={model.part1.routeSummary} labelKey="route_name" valueKey="passengers" color="#80c8ff" />
          </Card>
        </div>
        <Card title="Boarding / Alighting">
          <StackedList rows={model.part1.topTotalStations} />
        </Card>
      </section>
      <aside className="space-y-4">
        <Card title="Route Load">
          <div className="grid gap-3">
            <Gauge label="선택 역 수" value={model.part1.stationCount} percent={model.part1.stationPercent} />
            <Gauge label="승차 인원" value={model.part1.boarding} percent={model.part1.boardingPercent} />
            <Gauge label="하차 인원" value={model.part1.alighting} percent={model.part1.alightingPercent} />
          </div>
        </Card>
        <Card title="Route Inventory">
          <BarList rows={model.part1.routeCounts} labelKey="label" valueKey="value" color="#63dca7" />
        </Card>
        <Card title="Station Table">
          <DataTable rows={model.part1.stationRows} columns={["line_name", "station_order", "station_name", "boarding_count", "alighting_count"]} />
        </Card>
      </aside>
    </div>
  );
}

function Part2({ model }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[330px_1fr]">
      <aside className="space-y-4">
        <ScreenTitle eyebrow="Pattern Monitor" title="시간·계절 패턴" desc="월별·계절별 공실률 변화를 확인합니다." compact />
        <Card title="Vacancy State">
          <div className="grid gap-3">
            <Gauge label="최근 평균 공실률" value={`${formatFixed(model.part2.recentAvg)}%`} percent={bounded(model.part2.recentAvg)} />
            <Gauge label="초과수요 월" value={`${model.part2.excessMonths}개월`} percent={(model.part2.excessMonths / 12) * 100} />
            <Gauge label="최저 공실률" value={`${formatFixed(model.part2.minVacancy)}%`} percent={bounded(model.part2.minVacancy)} />
          </div>
        </Card>
        <Card title="Season Average">
          <BarList rows={model.part2.seasonStats} labelKey="label" valueKey="value" color="#63dca7" signed />
        </Card>
      </aside>
      <section className="space-y-4">
        <Card title="Monthly Vacancy Pattern">
          <MonthBars rows={model.part2.monthStats} />
        </Card>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Recent Vacancy Trend">
            <LineChart rows={model.part2.recentTrend} xKey="yearmonth" yKeys={[{ key: "공실률", label: "공실률", color: "#5db8ff" }]} />
          </Card>
          <Card title="Holiday Test">
            <DataTable rows={model.part2.holidayRows} columns={["노선", "명절달_평균공실률", "비명절달_평균공실률", "차이_pct", "p_value"]} />
          </Card>
        </div>
      </section>
    </div>
  );
}

function ForecastPanel({ model, mode, setMode }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-2 rounded-2xl border border-slate-200 bg-white/85 p-2 shadow-sm sm:grid-cols-2">
        {forecastModes.map((item) => {
          const active = mode === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setMode(item.id)}
              className={[
                "rounded-xl border px-4 py-3 text-left transition",
                active
                  ? "border-[#72ddb0] bg-[#e5fbf0] text-slate-900"
                  : "border-transparent bg-transparent text-slate-500 hover:bg-slate-50",
              ].join(" ")}
            >
              <span className="font-mono text-xs font-black tracking-[0.14em]">{item.code}</span>
              <span className="ml-3 text-sm font-black">{item.title}</span>
              <span className="ml-3 text-xs font-semibold">{item.desc}</span>
            </button>
          );
        })}
      </div>
      {mode === "regression" ? <Part3 model={model} /> : <Part4 model={model} />}
    </div>
  );
}

function Part3({ model }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr_340px]">
      <aside className="space-y-4">
        <ScreenTitle eyebrow="3-A Main Model" title="공실률 회귀 예측" desc="메인 모델의 예측 성능과 주요 영향 요인을 봅니다." compact />
        <Card title="Model Score">
          <div className="grid gap-3">
            <Metric label="통합 CatBoost MAE" value={`${formatFixed(model.part3.unifiedMae, 2)} pp`} />
            <Metric label="개별 모델 평균 MAE" value={`${formatFixed(model.part3.routeMaeAvg, 2)} pp`} />
            <Metric label="개별 모델 평균 RMSE" value={`${formatFixed(model.part3.routeRmseAvg, 2)} pp`} />
          </div>
        </Card>
        <Card title="Per Route Model">
          <DataTable rows={model.part3.routeComparison} columns={["노선", "개별모델_MAE", "개별모델_RMSE", "데이터수(행)"]} />
        </Card>
      </aside>
      <section className="space-y-4">
        <Card title="Vacancy SHAP Impact">
          <BarList rows={model.part3.shapTop} labelKey="feature" valueKey="mean_abs_shap" color="#f5b45f" />
        </Card>
        <Card title="Route MAE">
          <BarList rows={model.part3.routeMaeRows} labelKey="노선" valueKey="개별모델_MAE" color="#5db8ff" />
        </Card>
      </section>
      <aside className="space-y-4">
        <Card title="Route SHAP Top">
          <BarList rows={model.part3.routeShapTop} labelKey="routeFeature" valueKey="SHAP중요도" color="#63dca7" />
        </Card>
        <Card title="Model Role">
          <InsightList
            rows={[
              "공실률 예측의 중심 모델은 lag feature와 노선·계절 변수를 반영한 CatBoost 회귀 모델입니다.",
              "SHAP 값은 공실률 예측에 크게 기여한 요인을 노선 관리자에게 설명하는 근거로 사용합니다.",
              "시계열 모델은 시간 흐름 기준선으로 비교해 최근 초과수요 구간의 한계를 확인합니다.",
            ]}
          />
        </Card>
      </aside>
    </div>
  );
}

function Part4({ model }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
      <aside className="space-y-4">
        <ScreenTitle eyebrow="3-B Time-Series" title="시계열 예측" desc="Prophet 예측과 실제 공실률을 비교합니다." compact />
        <Card title="Prophet Holdout">
          <div className="grid gap-3">
            <Gauge label="MAE pp" value={formatFixed(model.part4.metric?.mae_pp)} percent={model.part4.metric?.mae_pp ?? 0} accent="#dc2626" />
            <Gauge label="RMSE pp" value={formatFixed(model.part4.metric?.rmse_pp)} percent={model.part4.metric?.rmse_pp ?? 0} accent="#f97316" />
            <Gauge label="평균 오차 pp" value={formatFixed(model.part4.metric?.mean_error_pp)} percent={Math.abs(model.part4.metric?.mean_error_pp ?? 0)} accent="#0ea5e9" />
          </div>
        </Card>
        <Card title="Time-Series Verdict">
          <InsightList
            rows={[
              "Prophet은 월별 공실률의 추세와 연간 계절성을 보는 기준선입니다.",
              "최근 초과수요처럼 음수 공실률이 강한 구간은 과거 추세만으로 따라가기 어렵습니다.",
              "정책 리포트에서는 Prophet 결과를 메인 모델의 보조 비교값으로 사용합니다.",
            ]}
          />
        </Card>
      </aside>
      <section className="space-y-4">
        <Card title="Actual vs Prophet Vacancy">
          <LineChart
            rows={model.part4.comparison}
            xKey="yearmonth"
            yKeys={[
              { key: "actual", label: "실제 공실률", color: "#5db8ff" },
              { key: "predicted", label: "Prophet 예측", color: "#ef6b6b" },
            ]}
          />
        </Card>
        <Card title="Holdout Comparison">
          <DataTable rows={model.part4.comparison} columns={["yearmonth", "노선", "actual", "predicted", "error", "abs_error"]} />
        </Card>
      </section>
    </div>
  );
}

function Part5({ model }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr_340px]">
      <aside className="space-y-4">
        <ScreenTitle eyebrow="Part 4 Interpretation" title="외부 변수 영향 분석" desc="공휴일·명절·코로나 같은 외부 요인이 공실률에 미친 신호를 해석합니다." compact />
        <Card title="External Signal">
          <BarList rows={model.part5.externalShapTop} labelKey="feature" valueKey="mean_abs_shap" color="#f5b45f" />
        </Card>
        <Card title="Holiday Test">
          <DataTable rows={model.part5.holidayRows} columns={["노선", "명절달_평균공실률", "비명절달_평균공실률", "차이_pct", "p_value"]} />
        </Card>
      </aside>
      <section className="space-y-4">
        <Card title="Holiday Vacancy Gap">
          <BarList rows={model.part5.holidayGapRows} labelKey="노선" valueKey="차이_pct" color="#5db8ff" signed />
        </Card>
        <Card title="Route External SHAP">
          <BarList rows={model.part5.externalRouteShapTop} labelKey="routeFeature" valueKey="SHAP중요도" color="#63dca7" />
        </Card>
      </section>
      <aside className="space-y-4">
        <Card title="Policy Reading">
          <InsightList
            rows={[
              "외부 변수 탭은 예측값 자체보다 왜 공실률이 흔들렸는지를 설명하는 해석 레이어입니다.",
              "명절·공휴일 신호가 큰 노선은 임시 증편, 좌석 배분, 사전 예약 유도 정책의 후보로 볼 수 있습니다.",
              "코로나 기간과 SRT 개통 후 변수는 구조적 변화 구간을 분리해 모델이 과거와 현재를 혼동하지 않게 합니다.",
            ]}
          />
        </Card>
      </aside>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <article className="dash-card rounded-2xl p-4">
      <h2 className="panel-title">{title}</h2>
      <div className="mt-3">{children}</div>
    </article>
  );
}

function ScreenTitle({ eyebrow, title, desc, compact = false }) {
  return (
    <div className={compact ? "pb-1" : "pb-2"}>
      <p className="text-xs font-bold tracking-[0.16em] text-slate-400">{eyebrow}</p>
      <h2 className="mt-1 text-3xl font-semibold tracking-tight text-slate-800">{title}</h2>
      <p className="mt-1 text-sm font-medium text-slate-500">{desc}</p>
    </div>
  );
}

function Gauge({ label, value, percent, accent = "#0f766e" }) {
  const angle = Math.max(8, Math.min(100, Math.abs(percent || 0)) * 2.7);
  return (
    <div className="rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-[#f5fbf8] p-3 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs font-black uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-black tabular-nums text-slate-950">{value}</p>
        </div>
        <div
          className="gauge-ring relative h-20 w-20 shrink-0 rounded-full"
          style={{ "--gauge-angle": `${angle}deg`, "--accent": accent, "--accent-2": "#72ddb0" }}
        >
          <div className="absolute inset-0 z-10 flex items-center justify-center pt-4 text-xs font-black text-slate-500">
            {Math.round(Math.abs(percent || 0))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
      <p className="text-xs font-bold text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-black tabular-nums text-slate-950">{value}</p>
    </div>
  );
}

function BarList({ rows, labelKey, valueKey, color, signed = false }) {
  const max = Math.max(...rows.map((row) => Math.abs(Number(row[valueKey] || 0))), 1);
  if (!rows.length) return <p className="text-sm text-slate-500">데이터 없음</p>;
  return (
    <div className="space-y-2">
      {rows.map((row, index) => {
        const value = Number(row[valueKey] || 0);
        const width = Math.max(3, (Math.abs(value) / max) * 100);
        const fill = signed && value < 0 ? "#dc2626" : color;
        return (
          <div key={`${row[labelKey]}-${index}`} className="grid grid-cols-[8rem_1fr_5.5rem] items-center gap-2 text-xs">
            <div className="truncate font-semibold text-slate-700" title={row[labelKey]}>{row[labelKey]}</div>
            <div className="bar-rail h-5 rounded-sm p-[2px]">
              <div className="bar-fill h-full rounded-[2px]" style={{ width: `${width}%`, "--bar-color": fill }} />
            </div>
            <div className="text-right font-mono tabular-nums text-slate-600">
              {signed ? formatFixed(value) : formatBarValue(value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StackedList({ rows }) {
  const max = Math.max(...rows.map((row) => Number(row.total_count || 0)), 1);
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const boarding = (Number(row.boarding_count || 0) / max) * 100;
        const alighting = (Number(row.alighting_count || 0) / max) * 100;
        return (
          <div key={row.station_name} className="grid grid-cols-[7rem_1fr_5.5rem] items-center gap-2 text-xs">
            <div className="truncate font-semibold text-slate-700" title={row.station_name}>{row.station_name}</div>
                <div className="bar-rail flex h-5 rounded-sm p-[2px]">
                  <div className="h-full rounded-l-[2px] bg-[#5db8ff]" style={{ width: `${boarding}%` }} />
                  <div className="h-full rounded-r-[2px] bg-[#f5b45f]" style={{ width: `${alighting}%` }} />
            </div>
            <div className="text-right font-mono tabular-nums text-slate-600">{formatNumber(row.total_count)}</div>
          </div>
        );
      })}
    </div>
  );
}

function MonthBars({ rows }) {
  const max = Math.max(...rows.map((row) => Math.abs(row.value)), 1);
  return (
    <div className="grid grid-cols-12 items-end gap-2">
      {rows.map((row) => {
        const height = Math.max(14, (Math.abs(row.value) / max) * 170);
        return (
          <div key={row.label} className="flex flex-col items-center gap-2">
            <div className="flex h-44 w-full items-end rounded-lg border border-slate-200 bg-slate-50 px-1">
              <div
                className="w-full rounded-t bg-gradient-to-t from-[#72ddb0] to-[#5db8ff]"
                style={{ height }}
                title={`${row.label}: ${formatFixed(row.value)}%`}
              />
            </div>
            <span className="font-mono text-[0.68rem] font-bold text-slate-500">{row.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function LineChart({ rows, xKey, yKeys }) {
  if (!rows.length) return <p className="text-sm text-slate-500">데이터 없음</p>;
  const width = 760;
  const height = 300;
  const pad = 28;
  const values = rows.flatMap((row) => yKeys.map((item) => Number(row[item.key])).filter(Number.isFinite));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const x = (index) => pad + (index / Math.max(rows.length - 1, 1)) * (width - pad * 2);
  const y = (value) => height - pad - ((value - min) / Math.max(max - min, 1)) * (height - pad * 2);
  return (
    <div className="overflow-x-auto thin-scroll">
      <svg width={width} height={height} className="min-w-[680px]">
        <line x1={pad} x2={width - pad} y1={y(0)} y2={y(0)} stroke="#cbd5e1" strokeDasharray="4 4" />
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const yy = pad + tick * (height - pad * 2);
          return <line key={tick} x1={pad} x2={width - pad} y1={yy} y2={yy} stroke="#e2e8f0" />;
        })}
        {yKeys.map((item) => {
          const points = rows.map((row, index) => `${x(index)},${y(Number(row[item.key] || 0))}`).join(" ");
          return <polyline key={item.key} points={points} fill="none" stroke={item.color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />;
        })}
        {rows.map((row, index) => (
          <text key={`${row[xKey]}-${index}`} x={x(index)} y={height - 6} textAnchor="middle" className="fill-slate-500 text-[10px]">
            {compactDate(row[xKey])}
          </text>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-3">
        {yKeys.map((item) => (
          <span key={item.key} className="flex items-center gap-2 text-xs font-bold text-slate-600">
            <span className="h-2 w-6 rounded-full" style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function DataTable({ rows, columns }) {
  const visibleRows = rows.slice(0, 14);
  return (
    <div className="max-h-[340px] overflow-auto thin-scroll rounded-lg border border-slate-200">
      <table className="min-w-full text-left text-xs">
        <thead className="sticky top-0 bg-slate-100 text-slate-600">
          <tr>
            {columns.map((column) => (
              <th key={column} className="whitespace-nowrap px-3 py-2 font-black">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white text-slate-700">
          {visibleRows.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-sky-50">
              {columns.map((column) => (
                <td key={column} className="whitespace-nowrap px-3 py-2">{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InsightList({ rows }) {
  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <p key={index} className="rounded-lg border border-slate-200 bg-white p-3 text-sm font-semibold leading-6 text-slate-700 shadow-sm">
          {row}
        </p>
      ))}
    </div>
  );
}

function buildViewModel(data, selectedRoute) {
  const part1Routes = sortRoutes(
    [...new Set(data.routeStations.map((row) => row.line_name).filter(Boolean))],
    part1RouteOrder,
  );
  const vacancyRoutes = sortRoutes(
    [...new Set(data.ktxLong.map((row) => row["노선"]).filter(Boolean))],
    vacancyRouteOrder,
  );
  const stationByName = new Map(data.stationSummary.map((row) => [row.station_name, row]));
  const stationRoute = data.routeStations.map((row) => ({
    ...row,
    ...(stationByName.get(row.station_name) || {}),
    boarding_count: Number(stationByName.get(row.station_name)?.boarding_count || 0),
    alighting_count: Number(stationByName.get(row.station_name)?.alighting_count || 0),
    total_count: Number(stationByName.get(row.station_name)?.total_count || 0),
  }));
  const routeFilter = (row) => selectedRoute === "전체" || row["노선"] === selectedRoute || row.line_name === selectedRoute || row.route_name === selectedRoute;
  const selectedStationRows = stationRoute.filter(routeFilter);
  const selectedStations = selectedRoute === "전체"
    ? data.stationSummary
    : uniqueBy(selectedStationRows, "station_name").sort((a, b) => b.boarding_count - a.boarding_count);
  const ktxRows = data.ktxLong.filter(routeFilter).sort((a, b) => String(a.yearmonth).localeCompare(String(b.yearmonth)));
  const recentTrend = ktxRows.slice(-12);
  const routeSummary = selectedRoute === "전체" ? data.routeSummary : data.routeSummary.filter(routeFilter);
  const currentProphetRoute = selectedRoute === "전체" ? "경부선" : selectedRoute;
  const shapRows = data.shapPerRoute.filter(routeFilter).map((row) => ({
    ...row,
    feature: featureLabel(row["변수"]),
    routeFeature: `${row["노선"]} · ${featureLabel(row["변수"])}`,
  }));
  const routeComparison = selectedRoute === "전체" ? data.routeModelComparison : data.routeModelComparison.filter(routeFilter);
  const unifiedMae = parseNumber(data.routeModelComparison[0]?.["통합모델_MAE"]);
  const holidayRows = selectedRoute === "전체" ? data.holidayMannWhitney : data.holidayMannWhitney.filter(routeFilter);
  const externalShapRows = shapRows.filter((row) => isExternalFeature(row["변수"]));

  return {
    part1Routes,
    vacancyRoutes,
    part1: {
      stationRows: selectedStationRows.sort((a, b) => String(a.line_name).localeCompare(String(b.line_name), "ko") || Number(a.station_order || 0) - Number(b.station_order || 0)),
      stationCount: selectedStations.length,
      stationPercent: (selectedStations.length / Math.max(data.stationSummary.length, 1)) * 100,
      boarding: sum(selectedStations, "boarding_count"),
      boardingPercent: (sum(selectedStations, "boarding_count") / Math.max(sum(data.stationSummary, "boarding_count"), 1)) * 100,
      alighting: sum(selectedStations, "alighting_count"),
      alightingPercent: (sum(selectedStations, "alighting_count") / Math.max(sum(data.stationSummary, "alighting_count"), 1)) * 100,
      topStations: top(selectedStations, "boarding_count", 12).reverse(),
      topTotalStations: top(selectedStations, "total_count", 12).reverse(),
      routeCounts: routeCounts(stationRoute),
      routeSummary: top(routeSummary, "passengers", 8).reverse(),
    },
    part2: {
      recentTrend,
      recentAvg: avg(recentTrend, "공실률"),
      minVacancy: min(recentTrend, "공실률"),
      excessMonths: recentTrend.filter((row) => Number(row["공실률"]) < 0).length,
      monthStats: monthStats(ktxRows),
      seasonStats: groupedAverage(ktxRows, "계절", "공실률"),
      holidayRows,
    },
    part3: {
      unifiedMae,
      routeMaeAvg: avg(routeComparison, "개별모델_MAE"),
      routeRmseAvg: avg(routeComparison, "개별모델_RMSE"),
      routeComparison,
      routeMaeRows: top(routeComparison, "개별모델_MAE", 8).reverse(),
      shapTop: top(aggregateShap(shapRows), "mean_abs_shap", 14).reverse(),
      routeShapTop: top(shapRows, "SHAP중요도", 10).reverse(),
    },
    part4: {
      metric: data.prophetMetrics.find((row) => row["노선"] === currentProphetRoute) || data.prophetMetrics[0],
      comparison: data.prophetComparison.filter((row) => row["노선"] === currentProphetRoute).sort((a, b) => String(a.yearmonth).localeCompare(String(b.yearmonth))),
    },
    part5: {
      holidayRows,
      holidayGapRows: topAbs(holidayRows, "차이_pct", 8).reverse(),
      externalShapTop: top(aggregateShap(externalShapRows), "mean_abs_shap", 10).reverse(),
      externalRouteShapTop: top(externalShapRows, "SHAP중요도", 10).reverse(),
    },
  };
}

function sortRoutes(routes, order) {
  return [...routes].sort((a, b) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b, "ko");
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

function routeCounts(rows) {
  const counts = new Map();
  rows.forEach((row) => {
    if (!counts.has(row.line_name)) counts.set(row.line_name, new Set());
    counts.get(row.line_name).add(row.station_name);
  });
  return [...counts.entries()]
    .map(([label, values]) => ({ label, value: values.size }))
    .sort((a, b) => a.value - b.value);
}

function monthStats(rows) {
  const stats = [];
  for (let month = 1; month <= 12; month += 1) {
    const selected = rows.filter((row) => Number(row["월"]) === month);
    stats.push({ label: `${month}`, value: avg(selected, "공실률") });
  }
  return stats;
}

function groupedAverage(rows, key, valueKey) {
  const groups = new Map();
  rows.forEach((row) => {
    const label = row[key] || "기타";
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(row);
  });
  return [...groups.entries()]
    .map(([label, values]) => ({ label, value: avg(values, valueKey) }))
    .sort((a, b) => a.value - b.value);
}

function aggregateShap(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const feature = row.feature || row["변수"];
    if (!groups.has(feature)) groups.set(feature, []);
    groups.get(feature).push(Number(row["SHAP중요도"] || 0));
  });
  return [...groups.entries()].map(([feature, values]) => ({
    feature,
    mean_abs_shap: values.reduce((total, value) => total + value, 0) / Math.max(values.length, 1),
  }));
}

function featureLabel(feature) {
  return {
    "공실률_lag1": "전월 공실률",
    "공실률_lag12": "전년 동월 공실률",
    "공실률_ma3": "3개월 이동평균",
    "월": "월",
    "분기": "분기",
    "계절": "계절",
    "코로나기간": "코로나 기간",
    "SRT개통후": "SRT 개통 후",
    "공휴일수": "공휴일 수",
    "명절연휴포함": "명절 연휴",
    "황금연휴포함": "황금연휴",
  }[feature] || feature;
}

function isExternalFeature(feature) {
  return ["코로나기간", "SRT개통후", "공휴일수", "명절연휴포함", "황금연휴포함"].includes(feature);
}

function uniqueBy(rows, key) {
  const seen = new Set();
  return rows.filter((row) => {
    if (seen.has(row[key])) return false;
    seen.add(row[key]);
    return true;
  });
}

function top(rows, key, limit) {
  return [...rows].sort((a, b) => Number(b[key] || 0) - Number(a[key] || 0)).slice(0, limit);
}

function topAbs(rows, key, limit) {
  return [...rows]
    .sort((a, b) => Math.abs(Number(b[key] || 0)) - Math.abs(Number(a[key] || 0)))
    .slice(0, limit);
}

function sum(rows, key) {
  return rows.reduce((total, row) => total + Number(row[key] || 0), 0);
}

function avg(rows, key) {
  if (!rows.length) return 0;
  return sum(rows, key) / rows.length;
}

function min(rows, key) {
  if (!rows.length) return 0;
  return Math.min(...rows.map((row) => Number(row[key] || 0)));
}

function bounded(value) {
  return Math.max(0, Math.min(100, Number(value || 0)));
}

function parseNumber(value) {
  const match = String(value ?? "").match(/-?\d+(\.\d+)?/);
  return match ? Number(match[0]) : 0;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

function formatFixed(value, digits = 1) {
  return Number(value || 0).toLocaleString("ko-KR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function formatBarValue(value) {
  if (Math.abs(value) < 100 && !Number.isInteger(value)) return formatFixed(value, 2);
  return formatNumber(value);
}

function formatCell(value) {
  if (typeof value === "number") {
    if (Math.abs(value) < 100 && !Number.isInteger(value)) return formatFixed(value, 3);
    return value.toLocaleString("ko-KR", { maximumFractionDigits: 3 });
  }
  return value ?? "";
}

function compactDate(value) {
  const text = String(value ?? "");
  if (text.length >= 7) return text.slice(2, 7).replace("-", ".");
  return text;
}
