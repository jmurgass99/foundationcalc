"""Catalogo de secciones estandar (EU + US). Unidades SI base (m)."""
from __future__ import annotations
from dataclasses import dataclass

# -----------------------------------------------------------------------------
# Perfiles I europeos (EN 10025) — HEA, HEB, IPE
# Dimensiones de EN 10365. Solo los más usados.
# -----------------------------------------------------------------------------

# Cada entrada: nombre -> (h, b, tw, tf) en metros
# h=peralte, b=ancho ala, tw=espesor alma, tf=espesor ala
_EU_I_SECTIONS = {
    # IPE — perfiles I delgados, vigas
    "IPE 100": (0.100, 0.055, 0.0041, 0.0057),
    "IPE 120": (0.120, 0.064, 0.0044, 0.0063),
    "IPE 140": (0.140, 0.073, 0.0047, 0.0069),
    "IPE 160": (0.160, 0.082, 0.0050, 0.0074),
    "IPE 180": (0.180, 0.091, 0.0053, 0.0080),
    "IPE 200": (0.200, 0.100, 0.0056, 0.0085),
    "IPE 220": (0.220, 0.110, 0.0059, 0.0092),
    "IPE 240": (0.240, 0.120, 0.0062, 0.0098),
    "IPE 270": (0.270, 0.135, 0.0066, 0.0102),
    "IPE 300": (0.300, 0.150, 0.0071, 0.0107),
    "IPE 330": (0.330, 0.160, 0.0075, 0.0115),
    "IPE 360": (0.360, 0.170, 0.0080, 0.0127),
    "IPE 400": (0.400, 0.180, 0.0086, 0.0135),
    "IPE 450": (0.450, 0.190, 0.0094, 0.0146),
    "IPE 500": (0.500, 0.200, 0.0102, 0.0160),
    "IPE 550": (0.550, 0.210, 0.0111, 0.0172),
    "IPE 600": (0.600, 0.220, 0.0120, 0.0190),
    # HEA — H europeos ligeros (columnas)
    "HEA 100": (0.096, 0.100, 0.0050, 0.0080),
    "HEA 120": (0.114, 0.120, 0.0050, 0.0080),
    "HEA 140": (0.133, 0.140, 0.0055, 0.0085),
    "HEA 160": (0.152, 0.160, 0.0060, 0.0090),
    "HEA 180": (0.171, 0.180, 0.0060, 0.0095),
    "HEA 200": (0.190, 0.200, 0.0065, 0.0100),
    "HEA 220": (0.210, 0.220, 0.0070, 0.0110),
    "HEA 240": (0.230, 0.240, 0.0075, 0.0120),
    "HEA 260": (0.250, 0.260, 0.0075, 0.0125),
    "HEA 280": (0.270, 0.280, 0.0080, 0.0130),
    "HEA 300": (0.290, 0.300, 0.0085, 0.0140),
    "HEA 320": (0.310, 0.300, 0.0090, 0.0155),
    "HEA 340": (0.330, 0.300, 0.0095, 0.0165),
    "HEA 360": (0.350, 0.300, 0.0100, 0.0175),
    "HEA 400": (0.390, 0.300, 0.0110, 0.0190),
    "HEA 450": (0.440, 0.300, 0.0115, 0.0210),
    "HEA 500": (0.490, 0.300, 0.0120, 0.0230),
    "HEA 550": (0.540, 0.300, 0.0125, 0.0240),
    "HEA 600": (0.590, 0.300, 0.0130, 0.0250),
    # HEB — H europeos pesados (columnas)
    "HEB 100": (0.100, 0.100, 0.0060, 0.0100),
    "HEB 120": (0.120, 0.120, 0.0065, 0.0110),
    "HEB 140": (0.140, 0.140, 0.0070, 0.0120),
    "HEB 160": (0.160, 0.160, 0.0080, 0.0130),
    "HEB 180": (0.180, 0.180, 0.0085, 0.0140),
    "HEB 200": (0.200, 0.200, 0.0090, 0.0150),
    "HEB 220": (0.220, 0.220, 0.0095, 0.0160),
    "HEB 240": (0.240, 0.240, 0.0100, 0.0170),
    "HEB 260": (0.260, 0.260, 0.0100, 0.0175),
    "HEB 280": (0.280, 0.280, 0.0105, 0.0180),
    "HEB 300": (0.300, 0.300, 0.0110, 0.0190),
    "HEB 320": (0.320, 0.300, 0.0115, 0.0205),
    "HEB 340": (0.340, 0.300, 0.0120, 0.0215),
    "HEB 360": (0.360, 0.300, 0.0125, 0.0225),
    "HEB 400": (0.400, 0.300, 0.0135, 0.0240),
    "HEB 450": (0.450, 0.300, 0.0140, 0.0260),
    "HEB 500": (0.500, 0.300, 0.0145, 0.0280),
    "HEB 550": (0.550, 0.300, 0.0150, 0.0290),
    "HEB 600": (0.600, 0.300, 0.0155, 0.0300),
}


# Perfiles I americanos (AISC) — selección común
# Nombre -> (h, b, tw, tf) en metros (convertidos desde inches)
_US_W_SECTIONS = {
    # W14 — columnas
    "W14X22":  (0.349, 0.127, 0.0058, 0.0084),
    "W14X30":  (0.353, 0.171, 0.0068, 0.0094),
    "W14X43":  (0.347, 0.203, 0.0077, 0.0135),
    "W14X53":  (0.354, 0.205, 0.0094, 0.0166),
    "W14X68":  (0.358, 0.255, 0.0105, 0.0181),
    "W14X90":  (0.356, 0.369, 0.0112, 0.0181),
    "W14X120": (0.368, 0.373, 0.0150, 0.0239),
    "W14X159": (0.380, 0.404, 0.0192, 0.0303),
    "W14X211": (0.398, 0.401, 0.0254, 0.0394),
    # W21 — vigas medianas
    "W21X44":  (0.525, 0.165, 0.0089, 0.0114),
    "W21X62":  (0.533, 0.210, 0.0102, 0.0157),
    "W21X83":  (0.544, 0.213, 0.0130, 0.0214),
    # W24
    "W24X55":  (0.599, 0.178, 0.0102, 0.0128),
    "W24X76":  (0.608, 0.229, 0.0114, 0.0173),
    "W24X94":  (0.617, 0.231, 0.0132, 0.0214),
    # W30
    "W30X90":  (0.752, 0.263, 0.0119, 0.0173),
    "W30X124": (0.762, 0.267, 0.0145, 0.0227),
}


_ALL = {**_EU_I_SECTIONS, **_US_W_SECTIONS}


@dataclass(frozen=True)
class IShape:
    """Perfil I (HEA/HEB/IPE/W) — geometria nominal."""
    name: str
    h: float    # peralte total
    b: float    # ancho de ala
    tw: float   # espesor de alma
    tf: float   # espesor de ala

    @property
    def family(self) -> str:
        for prefix in ("IPE", "HEA", "HEB", "W"):
            if self.name.upper().startswith(prefix):
                return prefix
        return "?"

    @property
    def A(self) -> float:
        """Area bruta (m²) — formula nominal."""
        return 2 * self.b * self.tf + (self.h - 2 * self.tf) * self.tw

    @property
    def Iy(self) -> float:
        """Inercia eje fuerte (m^4)."""
        hw = self.h - 2 * self.tf
        return (self.b * self.h**3 - (self.b - self.tw) * hw**3) / 12.0

    @property
    def Iz(self) -> float:
        """Inercia eje debil (m^4)."""
        hw = self.h - 2 * self.tf
        return (2 * self.tf * self.b**3 + hw * self.tw**3) / 12.0


def get_section(name: str) -> IShape:
    """Devuelve IShape para `name`. Lanza KeyError si no existe."""
    name = name.upper().strip()
    if name not in _ALL:
        # Buscar coincidencia parcial para ayudar
        candidates = [k for k in _ALL if name in k.upper()]
        hint = f" Sugerencias: {candidates[:5]}" if candidates else ""
        raise KeyError(f"Seccion '{name}' no esta en el catalogo.{hint}")
    h, b, tw, tf = _ALL[name]
    return IShape(name=name, h=h, b=b, tw=tw, tf=tf)


def list_sections(family: str | None = None) -> list[str]:
    """Lista las secciones disponibles, opcionalmente filtradas por familia."""
    if family is None:
        return sorted(_ALL.keys())
    family = family.upper()
    return sorted(k for k in _ALL if k.upper().startswith(family))


def define_in_sap(sap, section_name: str, material: str = "S355") -> str:
    """
    Define una seccion I del catalogo en SAP via FrameObj.PropFrame.SetISection.

    Esto SI llama a SAP — no se testea aqui sin pythonnet.

    Parameters
    ----------
    sap : SapClient activo
    section_name : nombre del catalogo (e.g. "HEA 300", "W14X68")
    material : nombre del material previamente definido

    Returns
    -------
    str : el nombre con el que quedo definida (igual a `section_name`)
    """
    from .utils import check_ret  # local import para evitar dep circular en tests
    s = get_section(section_name)
    # PropFrame.SetISection(Name, MatProp, T3, T2, Tf, Tw, T2b, Tfb, Color, Notes, GUID)
    # T3=h, T2=b sup, Tf=tf sup, Tw=tw, T2b=b inf, Tfb=tf inf (perfil simetrico)
    check_ret(
        sap.SapModel.PropFrame.SetISection(
            s.name, material, s.h, s.b, s.tf, s.tw, s.b, s.tf, -1, "", ""
        ),
        f"PropFrame.SetISection({s.name})",
    )
    return s.name
