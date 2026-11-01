import assert from "node:assert/strict";
import { solveFoundationWasm } from "../solver/wasmSolver.ts";

const layers = [
  { id: "CLAY-UPPER", thicknessM: 3.0, gammaEffKnM3: 9.2, e0: 0.9, Cc: 0.30, cvM2Yr: 2.2 },
  { id: "CLAY-LOWER", thicknessM: 4.0, gammaEffKnM3: 10.4, e0: 0.78, Cc: 0.22, cvM2Yr: 1.8 },
];

const resEarly = await solveFoundationWasm(2.6, 165, layers, 4, 0.4);
const resLate = await solveFoundationWasm(2.6, 165, layers, 8, 5.0);

assert.equal(resEarly.sublayers.length, 8);
assert.equal(resLate.sublayers.length, 16);
assert.equal(resLate.mapping.layerToSublayers.get("CLAY-UPPER")?.length, 8);
assert.ok(resLate.degreeU > resEarly.degreeU, "Consolidation degree U must increase with time");
assert.ok(resLate.sUltMm > 20, "Ultimate settlement must be positive");
console.log(
  `FoundationCalc WASM test OK: U(0.4y)=${(resEarly.degreeU * 100).toFixed(1)}%, U(5.0y)=${(resLate.degreeU * 100).toFixed(1)}%, s_ult=${resLate.sUltMm.toFixed(1)} mm`
);
