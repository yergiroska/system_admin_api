from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from app.database import get_db
from app.models import Customer
from app.schemas import CustomerResponse, CustomerDetailResponse, CustomerCreate

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

@router.post("/", response_model=CustomerResponse)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(
        **data.model_dump(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.deleted_at.is_(None)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    customer.first_name = data.first_name
    customer.last_name = data.last_name
    customer.birth_date = data.birth_date
    customer.identity_document = data.identity_document
    customer.image_url = data.image_url
    customer.updated_at = datetime.now()
    db.commit()
    db.refresh(customer)
    return customer

@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.deleted_at.is_(None)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    customer.deleted_at = datetime.now()
    db.commit()
    return {"message": f"Cliente '{customer.first_name} {customer.last_name}' eliminado correctamente"}

