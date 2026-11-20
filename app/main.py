from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.exceptions import AppException
from app.routes.router_health import router as health_router
from app.routes.routes_customer import router as customer_router
from app.routes.routes_order import router as order_router
from app.routes.routes_product import router as product_router


app = FastAPI(title="Orders API")


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


app.include_router(health_router)
app.include_router(customer_router)
app.include_router(order_router)
app.include_router(product_router)
