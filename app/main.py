from fastapi import FastAPI

from app.routes.router_health import router as health_router
from app.routes.routes_order import router as order_router

app = FastAPI(title="Orders API")

app.include_router(health_router)
app.include_router(order_router)

