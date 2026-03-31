from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import io

from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, CompanyProductPrice

router = APIRouter(
    prefix="/charts",
    tags=["Charts"]
)


@router.get("/sales-by-company")
def chart_sales_by_company(db: Session = Depends(get_db)):
    results = (
        db.query(
            Company.name,
            func.sum(Purchase.total).label("total_sales")
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .limit(10)
        .all()
    )

    df = pd.DataFrame(results, columns=["company", "total_sales"])

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(df["company"], df["total_sales"], color="steelblue")
    ax.set_xlabel("Ventas totales (€)")
    ax.set_title("Top 10 empresas por ventas")
    ax.invert_yaxis()

    for bar, value in zip(bars, df["total_sales"]):
        ax.text(value + 50, bar.get_y() + bar.get_height() / 2,
                f"€{value:,.2f}", va="center", fontsize=9)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")


@router.get("/top-products")
def chart_top_products(db: Session = Depends(get_db)):
    results = (
        db.query(
            Product.name,
            func.sum(Purchase.quantity).label("total_quantity")
        )
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(func.sum(Purchase.quantity).desc())
        .limit(10)
        .all()
    )

    df = pd.DataFrame(results, columns=["product", "total_quantity"])

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df["product"], df["total_quantity"], color="coral")
    ax.set_ylabel("Cantidad vendida")
    ax.set_title("Top 10 productos más vendidos")
    plt.xticks(rotation=45, ha="right")

    for bar, value in zip(bars, df["total_quantity"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(value), ha="center", fontsize=9)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")


@router.get("/purchases-by-month")
def chart_purchases_by_month(db: Session = Depends(get_db)):
    results = (
        db.query(
            func.date_trunc('month', Purchase.created_at).label("month"),
            func.sum(Purchase.total).label("total_sales")
        )
        .group_by(func.date_trunc('month', Purchase.created_at))
        .order_by(func.date_trunc('month', Purchase.created_at).asc())
        .all()
    )

    df = pd.DataFrame(results, columns=["month", "total_sales"])
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%Y-%m")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["month"], df["total_sales"], marker="o", color="steelblue", linewidth=2)
    ax.fill_between(df["month"], df["total_sales"], alpha=0.1, color="steelblue")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Ventas totales (€)")
    ax.set_title("Ventas por mes")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")


@router.get("/price-history/{product_id}")
def chart_price_history(product_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(
            Company.name.label("company"),
            CompanyProductPrice.price,
            CompanyProductPrice.created_at
        )
        .join(CompanyProduct, CompanyProduct.id == CompanyProductPrice.company_product_id)
        .join(Company, Company.id == CompanyProduct.company_id)
        .filter(CompanyProduct.product_id == product_id)
        .order_by(CompanyProductPrice.created_at.asc())
        .all()
    )

    df = pd.DataFrame(results, columns=["company", "price", "date"])
    df["price"] = df["price"].astype(float)

    fig, ax = plt.subplots(figsize=(12, 6))
    for company, group in df.groupby("company"):
        ax.plot(group["date"], group["price"], marker="o", label=company, linewidth=1.5)

    ax.set_xlabel("Fecha")
    ax.set_ylabel("Precio (€)")
    ax.set_title(f"Historial de precios — Producto #{product_id}")
    ax.legend(fontsize=7, loc="upper left")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")