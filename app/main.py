from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import companies, products, customers, purchases, stats, charts, reports, ml, auth, dashboard

app = FastAPI(title="System Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
def root():
    return {"message": "System Admin API funcionandooo"}