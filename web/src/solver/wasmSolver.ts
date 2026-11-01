import type { FoundationResult, SemanticSoilLayer } from "../data-model.ts";
import { getFoundationSublayerMesh } from "../mesh/getMesh.ts";

// Binario WebAssembly compilado desde consolidationKernel.cpp (exporta fdConsolidationNode y bulbStress2to1)
const WASM_B64 =
  "AGFzbQEAAAABEAJgBHx8fHwBfGADfHx8AXwDAwIAAQcoAhNmZENvbnNvbGlkYXRpb25Ob2RlAAAOYnVsYlN0cmVzczJ0bzEAAQozAhoAIAEgAyAARAAAAAAAAABAIAGioSACoKKgCxYAIAAgAaIgAaIgASACoCABIAKgoqML";

function decodeBase64(b64: string): Uint8Array {
  if (typeof Buffer !== "undefined") {
    return new Uint8Array(Buffer.from(b64, "base64"));
  }
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export interface FoundationWasmExports {
  fdConsolidationNode: (uPrev: number, uCurr: number, uNext: number, alpha: number) => number;
  bulbStress2to1: (qNet: number, B: number, z: number) => number;
}

let cachedExports: FoundationWasmExports | null = null;

export async function initFoundationWasm(): Promise<FoundationWasmExports> {
  if (cachedExports) return cachedExports;
  const bytes = decodeBase64(WASM_B64);
  const { instance } = await WebAssembly.instantiate(bytes);
  cachedExports = instance.exports as unknown as FoundationWasmExports;
  return cachedExports;
}

export async function solveFoundationWasm(
  widthBM: number,
  qNetKpa: number,
  layers: SemanticSoilLayer[],
  divisionsPerLayer: number,
  timeYears: number
): Promise<FoundationResult> {
  const wasm = await initFoundationWasm();
  const { sublayers, mapping } = getFoundationSublayerMesh(widthBM, qNetKpa, layers, divisionsPerLayer);

  const n = sublayers.length;
  for (let i = 0; i < n; i++) {
    sublayers[i].deltaSigmaKpa = wasm.bulbStress2to1(qNetKpa, widthBM, sublayers[i].zMidM);
    sublayers[i].excessPorePressureKpa = sublayers[i].deltaSigmaKpa;
  }

  // Evolución explícita en diferencias finitas 1D con drenaje superior e inferior (u=0 en bordes)
  const totalH = layers.reduce((acc, l) => acc + l.thicknessM, 0);
  const dzAvg = totalH / Math.max(n, 1);
  const cvAvg = layers.reduce((acc, l) => acc + l.cvM2Yr * l.thicknessM, 0) / Math.max(totalH, 1e-6);
  const alphaTarget = 0.25;
  const dtStep = (alphaTarget * dzAvg * dzAvg) / Math.max(cvAvg, 1e-6);
  const steps = Math.min(800, Math.max(1, Math.round(timeYears / dtStep)));
  const alpha = Math.min(0.45, (cvAvg * (timeYears / steps)) / (dzAvg * dzAvg));

  let u = sublayers.map((s) => s.deltaSigmaKpa);
  for (let step = 0; step < steps; step++) {
    const nextU = new Array<number>(n);
    for (let i = 0; i < n; i++) {
      const uPrev = i === 0 ? 0.0 : u[i - 1];
      const uNext = i === n - 1 ? 0.0 : u[i + 1];
      nextU[i] = Math.max(0.0, wasm.fdConsolidationNode(uPrev, u[i], uNext, alpha));
    }
    u = nextU;
  }

  let sumInitialArea = 0;
  let sumRemainingArea = 0;
  let sUltMm = 0;
  let qMaxBulbKpa = 0;

  for (let i = 0; i < n; i++) {
    sublayers[i].excessPorePressureKpa = u[i];
    sumInitialArea += sublayers[i].deltaSigmaKpa * sublayers[i].dzM;
    sumRemainingArea += u[i] * sublayers[i].dzM;
    sUltMm += sublayers[i].settlementUltMm;
    if (sublayers[i].deltaSigmaKpa > qMaxBulbKpa) qMaxBulbKpa = sublayers[i].deltaSigmaKpa;
  }

  const degreeU = sumInitialArea > 0 ? Math.min(1, Math.max(0, 1 - sumRemainingArea / sumInitialArea)) : 0;

  return {
    sublayers,
    mapping,
    sUltMm,
    sTimeMm: sUltMm * degreeU,
    degreeU,
    qMaxBulbKpa,
  };
}
