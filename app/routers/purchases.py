from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models import Purchase, CompanyProduct, Product, Company
from app.schemas import PurchaseResponse, PurchaseCreate

router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"]
)


@router.get("/", response_model=List[PurchaseResponse])
def get_purchases(db: Session = Depends(get_db)):
    purchases = (
        db.query(Purchase)
        .options(
            joinedload(Purchase.customer),
            joinedload(Purchase.company_product)
        )
        .all()
    )
    return [
        PurchaseResponse(
            id=p.id,
            customer=f"{p.customer.first_name} {p.customer.last_name}",
            unit_price=float(p.unit_price),
            quantity=p.quantity,
            total=float(p.total),
            created_at=p.created_at,
        )
        for p in purchases
    ]


@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    purchase = (
        db.query(Purchase)
        .filter(Purchase.id == purchase_id)
        .options(
            joinedload(Purchase.customer),
            joinedload(Purchase.company_product)
        )
        .first()
    )
    if not purchase:
        return {"error": "Compra no encontrada"}

    return PurchaseResponse(
        id=purchase.id,
        customer=f"{purchase.customer.first_name} {purchase.customer.last_name}",
        unit_price=float(purchase.unit_price),
        quantity=purchase.quantity,
        total=float(purchase.total),
        created_at=purchase.created_at,
    )

@router.post("/", response_model=PurchaseResponse)
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db)):
    company_product = db.query(CompanyProduct).filter(
        CompanyProduct.id == data.company_product_id
    ).first()
    if not company_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    total = data.unit_price * data.quantity

    purchase = Purchase(
        customer_id=data.customer_id,
        company_product_id=data.company_product_id,
        unit_price=data.unit_price,
        quantity=data.quantity,
        total=total,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    return PurchaseResponse(
        id=purchase.id,
        customer=f"{purchase.customer.first_name} {purchase.customer.last_name}",
        unit_price=float(purchase.unit_price),
        quantity=purchase.quantity,
        total=float(purchase.total),
        created_at=purchase.created_at,
    )

@router.get("/customer/{customer_id}")
def get_purchases_by_customer(customer_id: int, db: Session = Depends(get_db)):
    purchases = (
        db.query(Purchase)
        .options(
            joinedload(Purchase.customer),
            joinedload(Purchase.company_product)
        )
        .filter(Purchase.customer_id == customer_id)
        .order_by(Purchase.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "product_name": p.company_product.product.name,
            "company_name": p.company_product.company.name,
            "unit_price": float(p.unit_price),
            "quantity": p.quantity,
            "total": float(p.total),
            "created_at": p.created_at,
        }
        for p in purchases
    ]