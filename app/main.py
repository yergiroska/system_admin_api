from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import companies, products, customers, purchases, stats, charts, reports, ml, auth, dashboard, company_products, alerts
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import logging_loki

logging_loki.emitter.LokiEmitter.level_tag = "level"

handler = logging_loki.LokiHandler(
    url="http://localhost:3100/loki/api/v1/push",
    tags={"application": "system-admin-api"},
    version="1",
)

logger = logging.getLogger("system-admin-api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)


app = FastAPI(title="System Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(purchases.router)
app.include_router(stats.router)
app.include_router(charts.router)
app.include_router(reports.router)
app.include_router(ml.router)
app.include_router(dashboard.router)
app.include_router(company_products.router)
app.include_router(alerts.router)


@app.get("/")
def root():
    return {"message": "System Admin API funcionandooo"}