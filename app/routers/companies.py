from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import Company
from app.schemas import CompanyResponse, CompanyDetailResponse, CompanyBase

router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)


@router.get("/", response_model=List[CompanyResponse])
def get_companies(db: Session = Depends(get_db)):
    return db.query(Company).filter(Company.deleted_at.is_(None)).all()


@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.deleted_at.is_(None))
        .options(joinedload(Company.company_products))
        .first()
    )
    if not company:
        return {"error": "Empresa no encontrada"}

    company.total_products = len(company.company_products)
    return company

@router.post("/", response_model=CompanyResponse)
def create_company(data: CompanyBase, db: Session = Depends(get_db)):
    company = Company(
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, data: CompanyBase,db: Session = Depends(get_db)):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.deleted_at.is_(None)
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    company.name = data.name
    company.description = data.description
    company.image_url = data.image_url
    company.updated_at = datetime.now()
    db.commit()
    db.refresh(company)
    return company

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.deleted_at.is_(None)
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    company.deleted_at = datetime.now()
    db.commit()
    return {"message": f"Empresa '{company.name}' eliminada correctamente"}


