from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Customer
from app.schemas import CustomerResponse, CustomerDetailResponse

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


@router.get("/", response_model=List[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    return db.query(Customer).filter(Customer.deleted_at.is_(None)).all()


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.deleted_at.is_(None))
        .first()
    )
    if not customer:
        return {"error": "Cliente no encontrado"}

    customer.total_purchases = len(customer.purchases)
    return customer