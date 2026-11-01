export interface SemanticSoilLayer {
  id: string;
  thicknessM: number;
  gammaEffKnM3: number;
  e0: number;
  Cc: number;
  cvM2Yr: number;
}

export interface SoilSublayerMapping {
  layerToSublayers: Map<string, number[]>;
  sublayerToLayer: Map<number, string>;
  pileToSegments: Map<string, number[]>;
}

export interface SublayerDiscretization {
  index: number;
  layerId: string;
  zMidM: number;
  dzM: number;
  sigmaV0Kpa: number;
  deltaSigmaKpa: number;
  excessPorePressureKpa: number;
  settlementUltMm: number;
}

export interface FoundationResult {
  sublayers: SublayerDiscretization[];
  mapping: SoilSublayerMapping;
  sUltMm: number;
  sTimeMm: number;
  degreeU: number;
  qMaxBulbKpa: number;
}
