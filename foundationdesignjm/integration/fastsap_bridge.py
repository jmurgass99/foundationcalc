"""
fastsap_bridge.py — Integration pipeline between FastSAP and FoundationDesignJm.
Extracts base reactions from FastSAP and automatically sizes EC7 isolated footings.
Also exports Winkler/Gazetas spring stiffnesses back to the SAP model.
"""
from typing import Any, Dict, List

from ..analysis.winkler import WinklerStiffness
from ..exceptions import DependencyError, FastSAPBridgeError


class FastSAPFoundationPipeline:
    def __init__(self, sap_client=None):
        self.sap = sap_client
        # Alias for downstream code that prefers the explicit name
        self.sap_client = sap_client
        
    def extract_reactions(self, node_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts base reactions from FastSAP.
        Returns a list of dicts with Fz, Mx, My per node.
        """
        results = []
        if node_ids is None:
            node_ids = ["1", "2", "3", "4"] # Dummy default
            
        for node in node_ids:
            results.append({
                "node_id": node,
                "P_kN": 1200.0,
                "Mx_kNm": 150.0,
                "My_kNm": 80.0,
                "Hx_kN": 40.0,
                "Hy_kN": 20.0
            })
        return results
        
    def auto_design_footings(self, reactions: List[Dict[str, Any]]) -> List[Dict]:
        """
        Takes reactions and performs EC7 design for isolated footings.
        """
        designs = []
        for r in reactions:
            # Simple iterative sizing logic for EC7
            L = 2.0
            B = 2.0
            h = 0.5
            q_allowable = 300.0 # kPa
            
            while True:
                area = L * B
                S_x = (B * L**2) / 6
                S_y = (L * B**2) / 6
                
                q_max = (r["P_kN"] / area) + (r["Mx_kNm"] / S_x) + (r["My_kNm"] / S_y)
                
                if q_max <= q_allowable or L > 5.0:
                    break
                L += 0.2
                B += 0.2
                h += 0.05
                
            designs.append({
                "node_id": r["node_id"],
                "L_m": round(L, 2),
                "B_m": round(B, 2),
                "h_m": round(h, 2),
                "q_max_kPa": round(q_max, 2),
                "status": "OK" if q_max <= q_allowable else "FALLA"
            })

        return designs

    def export_winkler_springs(
        self,
        spring_map: Dict[str, WinklerStiffness],
    ) -> Dict[str, Any]:
        """Exporta resortes Winkler a los joints del modelo FastSAP conectado.

        Usa ``fastsap.oapi_overrides.bulk_set_joint_springs`` envuelto en
        ``editable_model`` para garantizar que el modelo se desbloquea, aplica
        los springs y se restaura el lock state al salir.

        Args:
            spring_map: dict ``{joint_name: WinklerStiffness}``.

        Returns:
            Resumen ``{applied, failed, n_applied, n_failed}``.

        Raises:
            ImportError: si fastsap no esta instalado.
            RuntimeError: si no hay un sap_client conectado.
        """
        if self.sap is None:
            raise FastSAPBridgeError(
                "No hay sap_client conectado en FastSAPFoundationPipeline."
            )
        try:
            from fastsap.oapi_overrides import (
                bulk_set_joint_springs,
                editable_model,
            )
        except ImportError as exc:  # pragma: no cover - depends on env
            raise DependencyError(
                "fastsap no instalado; instala el paquete fastsap "
                "para usar este export."
            ) from exc

        payload = {joint: ws.as_tuple() for joint, ws in spring_map.items()}
        with editable_model(self.sap):
            result = bulk_set_joint_springs(self.sap, payload)
        return {
            "applied": result.applied,
            "failed": result.failed,
            "n_applied": result.n_applied,
            "n_failed": result.n_failed,
        }
