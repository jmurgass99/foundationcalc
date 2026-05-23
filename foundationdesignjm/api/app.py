"""FastAPI app exponiendo los servicios de FoundationDesignJm."""
from __future__ import annotations

from contextlib import asynccontextmanager

try:
    from fastapi import APIRouter, FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as exc:
    raise ImportError(
        "fastapi requerido: pip install foundationdesignjm[api]"
    ) from exc

from .._brand import NAME as _BRAND_NAME
from ..services import footings, walls, piles, bearing, seismic
from ..jobs import JobQueue
from ..jobs.api import router as _jobs_router, set_queue as _set_jobs_queue


router = APIRouter()


@router.get("/")
def root():
    return {
        "name": _BRAND_NAME,
        "endpoints": [
            "/api/footings/isolated",
            "/api/walls/cantilever",
            "/api/piles/axial",
            "/api/bearing/multilayer",
            "/api/seismic/mononobe_okabe",
            "/jobs/*",
        ],
    }


@router.post("/api/footings/isolated")
def api_isolated_footing(inp: dict):
    try:
        result = footings.design_isolated_footing(
            footings.IsolatedFootingInput(**inp)
        )
        return {
            "pressures": result.pressures,
            "punching": result.punching,
            "flexure_x": result.flexure_x,
            "flexure_y": result.flexure_y,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/walls/cantilever")
def api_cantilever_wall(inp: dict):
    try:
        result = walls.design_cantilever_wall(walls.CantileverWallInput(**inp))
        return {
            "sliding_FS": result.sliding_FS,
            "overturning_FS": result.overturning_FS,
            "bearing_FS": result.bearing_FS,
            "stem_design": result.stem_design,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/piles/axial")
def api_pile_axial(inp: dict):
    try:
        if "layers_qu_kPa" in inp:
            inp["layers_qu_kPa"] = tuple(inp["layers_qu_kPa"])
        if "layers_thickness" in inp:
            inp["layers_thickness"] = tuple(inp["layers_thickness"])
        result = piles.design_pile_axial(piles.PileAxialInput(**inp))
        return {
            "Q_skin_kN": result.Q_skin_kN,
            "Q_tip_kN": result.Q_tip_kN,
            "Q_ultimate_kN": result.Q_ultimate_kN,
            "Q_allowable_kN": result.Q_allowable_kN,
            "FS": result.FS,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/bearing/multilayer")
def api_bearing(inp: dict):
    try:
        layers = tuple(bearing.SoilLayerSpec(**l)
                       for l in inp.pop("layers", []))
        result = bearing.bearing_capacity_multilayer(
            bearing.BearingInput(layers=layers, **inp)
        )
        return {
            "qu_kPa": result.qu_kPa,
            "qa_kPa": result.qa_kPa,
            "FS": result.FS,
            "method": result.method,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/seismic/mononobe_okabe")
def api_mo(inp: dict):
    try:
        result = seismic.mononobe_okabe_thrust(seismic.MononobeOkabeInput(**inp))
        return {
            "K_AE": result.K_AE,
            "P_AE_kN_per_m": result.P_AE,
            "theta_deg": result.theta,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(400, str(exc))


def create_router() -> APIRouter:
    """Devuelve el APIRouter (factory para uniformidad con otros repos).

    Nota: el jobs router (_jobs_router) NO se incluye aquí — solo las rutas
    de cálculo. La cola de jobs es estado por proceso y debe configurarse
    a nivel app standalone (vía lifespan) o a nivel gateway.
    """
    return router


# ---------------------------------------------------------------------------
# App standalone (con jobs queue y CORS)
# ---------------------------------------------------------------------------
# Job queue lifecycle (solo en app standalone). Reemplaza los @app.on_event
# deprecados por un gestor de contexto lifespan moderno de FastAPI.
_job_queue: JobQueue | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _job_queue
    _job_queue = JobQueue(numerical_workers=4)
    _set_jobs_queue(_job_queue)
    try:
        yield
    finally:
        if _job_queue is not None:
            _job_queue.shutdown(wait=True)


app = FastAPI(title=f"{_BRAND_NAME} API", version="0.1.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)
app.include_router(_jobs_router)
