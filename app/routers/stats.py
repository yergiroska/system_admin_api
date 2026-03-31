from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, CompanyProductPrice

router = APIRouter(
    prefix="/stats",
    tags=["Stats"]
)


@router.get("/sales-by-company")
def sales_by_company(db: Session = Depends(get_db)):
    results = (
        db.query(
            Company.name,
            func.sum(Purchase.total).label("total_sales"),
            func.count(Purchase.id).label("total_purchases")
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .all()
    )
    return [
        {
            "company": r.name,
            "total_sales": round(float(r.total_sales), 2),
            "total_purchases": r.total_purchases,
        }
        for r in results
    ]


@router.get("/top-products")
def top_products(db: Session = Depends(get_db)):
    results = (
        db.query(
            Product.name,
            func.sum(Purchase.quantity).label("total_quantity"),
            func.sum(Purchase.total).label("total_sales")
        )
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(func.sum(Purchase.quantity).desc())
        .limit(10)
        .all()
    )
    return [
        {
            "product": r.name,
            "total_quantity": int(r.total_quantity),
            "total_sales": round(float(r.total_sales), 2),
        }
        for r in results
    ]


@router.get("/price-history/{product_id}")
def price_history(product_id: int, db: Session = Depends(get_db)):
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
    return [
        {
            "company": r.company,
            "price": round(float(r.price), 2),
            "date": r.created_at,
        }
        for r in results
    ]


@router.get("/purchases-by-month")
def purchases_by_month(db: Session = Depends(get_db)):
    results = (
        db.query(
            func.date_trunc('month', Purchase.created_at).label("month"),
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_sales")
        )
        .group_by(func.date_trunc('month', Purchase.created_at))
        .order_by(func.date_trunc('month', Purchase.created_at).asc())
        .all()
    )
    return [
        {
            "month": r.month.strftime("%Y-%m"),
            "total_purchases": r.total_purchases,
            "total_sales": round(float(r.total_sales), 2),
        }
        for r in results
    ]