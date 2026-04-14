from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List


# ─── Company ───────────────────────────────────────────
class CompanyBase(BaseModel):
    name: str
    description: str
    image_url: Optional[str] = None


class CompanyResponse(CompanyBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(CompanyResponse):
    total_products: int


# ─── Product ───────────────────────────────────────────
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    total_companies: int


# ─── Customer ──────────────────────────────────────────
class CustomerBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    identity_document: Optional[str] = None

class CustomerCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    identity_document: Optional[str] = None
    image_url: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: int
    birth_date: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerDetailResponse(CustomerResponse):
    total_purchases: int


# ─── Purchase ──────────────────────────────────────────
class PurchaseResponse(BaseModel):
    id: int
    customer: str
    unit_price: float
    quantity: int
    total: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PurchaseCreate(BaseModel):
    customer_id: int
    company_product_id: int
    quantity: int
    unit_price: float

# ─── Stats ─────────────────────────────────────────────
class SalesByCompanyResponse(BaseModel):
    company: str
    total_sales: float
    total_purchases: int


class TopProductResponse(BaseModel):
    product: str
    total_quantity: int
    total_sales: float


class PriceHistoryResponse(BaseModel):
    company: str
    price: float
    date: Optional[datetime] = None


class PurchasesByMonthResponse(BaseModel):
    month: str
    total_purchases: int
    total_sales: float


# ─── Company Product ───────────────────────────────────
class CompanyProductCreate(BaseModel):
    product_id: int
    company_id: int
    price: float