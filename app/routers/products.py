from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductDetailResponse, ProductBase
import logging
logger = logging.getLogger("system-admin-api")

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.get("/", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    logger.info("Listando products")
    return db.query(Product).filter(Product.deleted_at.is_(None)).all()


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.deleted_at.is_(None))
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.total_companies = len(product.company_products)
    return product

@router.post("/", response_model=ProductResponse)
def create_product(data: ProductBase, db: Session = Depends(get_db)):
    product = Product(
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductBase, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None)
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.name = data.name
    product.description = data.description
    product.image_url = data.image_url
    product.updated_at = datetime.now()
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None)
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.deleted_at = datetime.now()
    db.commit()
    return {"message": f"Producto '{product.name}' eliminado correctamente"}
