from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models import Purchase
from app.schemas import PurchaseResponse

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