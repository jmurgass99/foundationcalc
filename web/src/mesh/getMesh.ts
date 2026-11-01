import { SemanticSoilLayer, SoilSublayerMapping, SublayerDiscretization } from "../data-model.ts";

export function getFoundationSublayerMesh(
  widthBM: number,
  qNetKpa: number,
  layers: SemanticSoilLayer[],
  divisionsPerLayer: number
): { sublayers: SublayerDiscretization[]; mapping: SoilSublayerMapping } {
  const div = Math.max(1, Math.floor(divisionsPerLayer));
  const layerToSublayers = new Map<string, number[]>();
  const sublayerToLayer = new Map<number, string>();
  const pileToSegments = new Map<string, number[]>();
  const sublayers: SublayerDiscretization[] = [];

  let zCursor = 0;
  let sigmaCursor = 12.0;

  for (const layer of layers) {
    const dz = layer.thicknessM / div;
    const indices: number[] = [];
    for (let i = 0; i < div; i++) {
      const idx = sublayers.length;
      const zMid = zCursor + 0.5 * dz;
      const sigmaV0 = sigmaCursor + 0.5 * dz * layer.gammaEffKnM3;
      const deltaSigma = (qNetKpa * widthBM * widthBM) / Math.pow(widthBM + zMid, 2);
      const sUltMm =
        ((dz * layer.Cc) / (1 + layer.e0)) *
        Math.log10((sigmaV0 + deltaSigma) / Math.max(sigmaV0, 1.0)) *
        1000;
      sublayers.push({
        index: idx,
        layerId: layer.id,
        zMidM: zMid,
        dzM: dz,
        sigmaV0Kpa: sigmaV0,
        deltaSigmaKpa: deltaSigma,
        excessPorePressureKpa: deltaSigma,
        settlementUltMm: sUltMm,
      });
      indices.push(idx);
      sublayerToLayer.set(idx, layer.id);
      zCursor += dz;
      sigmaCursor += dz * layer.gammaEffKnM3;
    }
    layerToSublayers.set(layer.id, indices);
  }

  pileToSegments.set(
    "PILE-GROUP-A",
    sublayers.map((s) => s.index)
  );

  return {
    sublayers,
    mapping: { layerToSublayers, sublayerToLayer, pileToSegments },
  };
}
