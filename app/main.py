from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import companies, products, customers, purchases, stats, charts, reports, ml, auth, dashboard, company_products, alerts
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import logging_loki

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource

# --- Loki logging ---
logging_loki.emitter.LokiEmitter.level_tag = "level"

handler = logging_loki.LokiHandler(
    url="http://localhost:3100/loki/api/v1/push",
    tags={"application": "system-admin-api"},
    version="1",
)

logger = logging.getLogger("system-admin-api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# --- OpenTelemetry setup ---
resource = Resource(attributes={"service.name": "system-admin-api"})
exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# --- FastAPI ---
app = FastAPI(title="System Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

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