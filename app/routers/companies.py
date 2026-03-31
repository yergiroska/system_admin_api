from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models import Company
from app.schemas import CompanyResponse, CompanyDetailResponse

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