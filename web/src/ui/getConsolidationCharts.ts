import { FoundationResult } from "../data-model.ts";

export function renderIsochroneChart(canvas: HTMLCanvasElement, res: FoundationResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const maxZ = Math.max(...res.sublayers.map((s) => s.zMidM + 0.5 * s.dzM), 1);
  const maxQ = Math.max(res.qMaxBulbKpa, 1);

  // Curva inicial Δσ(z) (naranja punteada) e isócrona actual u(z,t) (azul sólida)
  ctx.strokeStyle = "#f59e0b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  res.sublayers.forEach((s, idx) => {
    const x = 36 + (s.deltaSigmaKpa / maxQ) * (w - 52);
    const y = 16 + (s.zMidM / maxZ) * (h - 38);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  res.sublayers.forEach((s, idx) => {
    const x = 36 + (s.excessPorePressureKpa / maxQ) * (w - 52);
    const y = 16 + (s.zMidM / maxZ) * (h - 38);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "11px Inter, sans-serif";
  ctx.fillText(`Isócrona u(z,t) vs Δσ(z) — U = ${(res.degreeU * 100).toFixed(1)}%`, 42, 30);
}

export function renderSettlementCurveChart(canvas: HTMLCanvasElement, res: FoundationResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const sMax = Math.max(...res.sublayers.map((s) => s.settlementUltMm), 0.1);
  const n = Math.max(res.sublayers.length, 1);
  const barH = (h - 42) / n;

  res.sublayers.forEach((s, idx) => {
    const bw = (s.settlementUltMm / sMax) * (w - 60);
    const y = 18 + idx * barH;
    ctx.fillStyle = s.layerId === "CLAY-UPPER" ? "#f59e0b" : "#34d399";
    ctx.fillRect(36, y, bw, Math.max(2, barH - 2));
  });

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "11px Inter, sans-serif";
  ctx.fillText(`Asiento por subcapa Δs_c (mm) — s_ult = ${res.sUltMm.toFixed(1)} mm`, 42, h - 8);
}
