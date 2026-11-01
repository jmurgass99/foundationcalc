import van from "vanjs-core";
import { SemanticSoilLayer } from "./data-model.ts";
import { solveFoundationWasm } from "./solver/wasmSolver.ts";
import { fetchIsolatedFootingApi } from "./solver/apiClient.ts";
import { createFoundationViewer3D } from "./viewer/getViewer3D.ts";
import { renderIsochroneChart, renderSettlementCurveChart } from "./ui/getConsolidationCharts.ts";

const { div, h2, h3, label, input, span, strong, canvas, button } = van.tags;

const widthBM = van.state(2.6);
const qNetKpa = van.state(165);
const divisions = van.state(6);
const timeYears = van.state(1.8);
const sUltText = van.state("0.0 mm");
const sTimeText = van.state("0.0 mm");
const degreeUText = van.state("0.0 %");
const sublayersText = van.state("12");
const apiStatus = van.state("Modo WASM local");

const viewerWrap = div({ class: "viewer-wrap" });
const isochroneCanvas = canvas({ class: "chart" });
const settlementCanvas = canvas({ class: "chart" });

const viewer = createFoundationViewer3D(viewerWrap);

const defaultLayers: SemanticSoilLayer[] = [
  { id: "CLAY-UPPER", thicknessM: 3.0, gammaEffKnM3: 9.2, e0: 0.9, Cc: 0.30, cvM2Yr: 2.2 },
  { id: "CLAY-LOWER", thicknessM: 4.0, gammaEffKnM3: 10.4, e0: 0.78, Cc: 0.22, cvM2Yr: 1.8 },
];

async function recompute() {
  const res = await solveFoundationWasm(
    widthBM.val,
    qNetKpa.val,
    defaultLayers,
    divisions.val,
    timeYears.val
  );
  sUltText.val = `${res.sUltMm.toFixed(1)} mm`;
  sTimeText.val = `${res.sTimeMm.toFixed(1)} mm`;
  degreeUText.val = `${(res.degreeU * 100).toFixed(1)} %`;
  sublayersText.val = `${res.sublayers.length}`;
  viewer.update(widthBM.val, res);
  renderIsochroneChart(isochroneCanvas, res);
  renderSettlementCurveChart(settlementCanvas, res);
}

van.derive(() => {
  void recompute();
});

const app = div(
  { class: "layout" },
  div(
    { class: "panel" },
    h2("FoundationCalc 3D"),
    div(
      { class: "control-row" },
      label(() => `Ancho de zapata B = ${widthBM.val.toFixed(1)} m`),
      input({
        type: "range",
        min: "1.4",
        max: "5.0",
        step: "0.2",
        value: widthBM,
        oninput: (e: Event) => (widthBM.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Presión neta q_net = ${qNetKpa.val} kPa`),
      input({
        type: "range",
        min: "60",
        max: "320",
        step: "5",
        value: qNetKpa,
        oninput: (e: Event) => (qNetKpa.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Subcapas por estrato (SoilSublayerMapping) = ${divisions.val}`),
      input({
        type: "range",
        min: "2",
        max: "16",
        step: "1",
        value: divisions,
        oninput: (e: Event) => (divisions.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Tiempo de consolidación t = ${timeYears.val.toFixed(1)} años`),
      input({
        type: "range",
        min: "0.1",
        max: "10.0",
        step: "0.1",
        value: timeYears,
        oninput: (e: Event) => (timeYears.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "kpi-grid" },
      div({ class: "kpi" }, span("Asiento s(t)"), strong(sTimeText)),
      div({ class: "kpi" }, span("Asiento final s_ult"), strong(sUltText)),
      div({ class: "kpi" }, span("Grado U(t)"), strong(degreeUText)),
      div({ class: "kpi" }, span("Subcapas activas"), strong(sublayersText))
    ),
    button(
      {
        onclick: async () => {
          const r = await fetchIsolatedFootingApi("http://localhost:8000", widthBM.val, qNetKpa.val);
          apiStatus.val = r.ok ? "FastAPI sincronizado OK" : "FastAPI offline (usando WASM local)";
        },
      },
      "Sincronizar con FastAPI"
    ),
    span({ style: "font-size:0.75rem;color:#94a3b8" }, apiStatus)
  ),
  viewerWrap,
  div(
    { class: "panel" },
    h3("Isócrona 1D Terzaghi (WASM FD)"),
    isochroneCanvas,
    h3("Asiento de Consolidación por Subcapa"),
    settlementCanvas
  )
);

document.getElementById("app")?.appendChild(app);
