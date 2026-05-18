import { readFile } from "node:fs/promises";
import path from "node:path";

const processedDir = path.join(process.cwd(), "..", "data", "processed");

const files = {
  stationSummary: "station_summary.csv",
  routeStations: "ktx_route_stations_standard.csv",
  routeSummary: "route_summary.csv",
  ktxLong: "ktx_long.csv",
  modelInput: "ktx_model_input.csv",
  shapPerRoute: "shap_per_route.csv",
  routeModelComparison: "model_comparison_per_route.csv",
  prophetMetrics: "part4_prophet_metrics.csv",
  prophetComparison: "part4_prophet_vacancy_comparison.csv",
  holidayMannWhitney: "holiday_mannwhitney.csv",
};

export async function getDashboardData() {
  const entries = await Promise.all(
    Object.entries(files).map(async ([key, filename]) => {
      const rows = await loadCsv(filename);
      return [key, rows];
    }),
  );

  const data = Object.fromEntries(entries);
  return {
    generatedAt: new Date().toISOString(),
    ...data,
  };
}

async function loadCsv(filename) {
  try {
    const text = await readFile(path.join(processedDir, filename), "utf8");
    return parseCsv(text);
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  const cleaned = text.replace(/^\uFEFF/, "");

  for (let i = 0; i < cleaned.length; i += 1) {
    const char = cleaned[i];
    const next = cleaned[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }

  const headers = rows.shift()?.map((header) => header.trim()) ?? [];
  return rows
    .filter((values) => values.some((value) => value !== ""))
    .map((values) => {
      const item = {};
      headers.forEach((header, index) => {
        item[header] = coerce(values[index] ?? "");
      });
      return item;
    });
}

function coerce(value) {
  const trimmed = String(value).trim();
  if (trimmed === "") return "";
  const normalized = trimmed.replaceAll(",", "");
  if (/^-?\d+(\.\d+)?$/.test(normalized)) return Number(normalized);
  return trimmed;
}
