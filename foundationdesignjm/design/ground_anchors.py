"""
ground_anchors.py — Design of ground anchors according to EC7 and ACI 318.
"""
from typing import Dict, Any

class GroundAnchor:
    """
    Design of post-tensioned or passive ground anchors.
    """
    def __init__(self, load_kN: float, free_length_m: float, bonded_length_m: float, 
                 hole_diameter_m: float, soil_grout_bond_kPa: float):
        self.load_kN = load_kN
        self.free_length = free_length_m
        self.bonded_length = bonded_length_m
        self.hole_diameter = hole_diameter_m
        self.q_bond = soil_grout_bond_kPa

    def pullout_capacity(self) -> float:
        """
        Geotechnical pullout capacity of the bonded length.
        """
        import math
        # Area of bond = pi * D * L_bond
        bond_area = math.pi * self.hole_diameter * self.bonded_length
        return bond_area * self.q_bond

    def structural_capacity(self, area_steel_mm2: float, fpe_MPa: float) -> float:
        """
        Structural capacity of the steel tendon.
        """
        return (area_steel_mm2 * fpe_MPa) / 1000.0 # kN

    def design_report(self) -> Dict[str, Any]:
        """
        Full design check for the ground anchor.
        """
        R_pullout = self.pullout_capacity()
        FS_pullout = R_pullout / self.load_kN if self.load_kN > 0 else 99.9
        
        return {
            "load_kN": self.load_kN,
            "bonded_length_m": self.bonded_length,
            "hole_diameter_m": self.hole_diameter,
            "R_pullout_kN": round(R_pullout, 2),
            "FS_pullout": round(FS_pullout, 2),
            "status": "OK" if FS_pullout >= 1.5 else "FAIL"
        }
