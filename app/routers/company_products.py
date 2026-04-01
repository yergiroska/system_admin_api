from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import CompanyProductCreate
from app.models import CompanyProduct, CompanyProductPrice, Company

router = APIRouter(
    prefix="/company-products",
    tags=["Company Products"]
)


@router.get("/product/{product_id}")
def get_companies_by_product(product_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(
            CompanyProduct.id,
            Company.id.label("company_id"),
            Company.name.label("company_name"),
            CompanyProductPrice.price,
        )
        .join(Company, Company.id == CompanyProduct.company_id)
        .join(CompanyProductPrice, CompanyProductPrice.company_product_id == CompanyProduct.id)
        .filter(
            CompanyProduct.product_id == product_id,
            CompanyProduct.deleted_at.is_(None)
        )
        .order_by(CompanyProduct.id, CompanyProductPrice.created_at.desc())
        .distinct(CompanyProduct.id)
        .all()
    )
    return [
        {
            "company_product_id": r.id,
            "company_id": r.company_id,
            "company_name": r.company_name,
            "price": float(r.price),
        }
        for r in results
    ]


@router.post("/")
def create_company_product(data: CompanyProductCreate, db: Session = Depends(get_db)):
    existing = db.query(CompanyProduct).filter(
        CompanyProduct.product_id == data.product_id,
        CompanyProduct.company_id == data.company_id,
        CompanyProduct.deleted_at.is_(None)
    ).first()

    if existing:
        price = CompanyProductPrice(
            company_product_id=existing.id,
            price=data.price,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(price)
        db.commit()
        return {"message": "Precio actualizado correctamente", "company_product_id": existing.id}

    cp = CompanyProduct(
        product_id=data.product_id,
        company_id=data.company_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(cp)
    db.flush()

    price = CompanyProductPrice(
        company_product_id=cp.id,
        price=data.price,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(price)
    db.commit()
    return {"message": "Asociación creada correctamente", "company_product_id": cp.id}