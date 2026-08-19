from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.datasets.routes import router as datasets_router
from app.api.v1.eda.routes import router as eda_router
from app.api.v1.kpi.routes import router as kpi_router
from app.api.v1.forecasting.routes import router as forecasting_router
from app.api.v1.ai.routes import router as ai_router
from app.api.v1.root_cause.routes import router as root_cause_router
from app.api.v1.simulation.routes import router as simulation_router
from app.api.v1.decision.routes import router as decision_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(eda_router)
api_router.include_router(kpi_router)
api_router.include_router(forecasting_router)
api_router.include_router(ai_router)
api_router.include_router(root_cause_router)
api_router.include_router(simulation_router)
api_router.include_router(decision_router)
