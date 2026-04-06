from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from groq import Groq
from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, Customer, CompanyProductPrice
from app.auth import get_current_user
from app.models import User
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"]
)

os.environ["OTEL_SDK_DISABLED"] = "true"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


def get_business_context(db: Session) -> str:
    total_purchases = db.query(func.count(Purchase.id)).scalar()
    total_revenue = db.query(func.sum(Purchase.total)).scalar() or 0
    total_customers = db.query(func.count(Customer.id)).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()

    top_company = (
        db.query(Company.name, func.sum(Purchase.total).label("total"))
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .first()
    )

    top_products = (
        db.query(Product.name, func.sum(Purchase.quantity).label("total"))
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(func.sum(Purchase.quantity).desc())
        .limit(5)
        .all()
    )

    top_products_str = ", ".join([f"{p.name} ({int(p.total)} unidades)" for p in top_products])

    top_companies = (
        db.query(Company.name, func.sum(Purchase.total).label("total"))
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .limit(5)
        .all()
    )

    top_companies_str = ", ".join([f"{c.name} (€{float(c.total):,.2f})" for c in top_companies])

    return f"""
    Eres un asistente de análisis de negocios para el sistema System Admin.
    Estos son los datos actuales del negocio:
    - Total de compras: {total_purchases}
    - Ingresos totales: €{float(total_revenue):,.2f}
    - Total de clientes: {total_customers}
    - Total de empresas: {total_companies}
    - Total de productos: {total_products}
    - Top 5 empresas por ventas: {top_companies_str}
    - Top 5 productos más vendidos: {top_products_str}

    Responde siempre en español, de forma clara y concisa.
    Basa tus respuestas SOLO en los datos reales del negocio proporcionados arriba.
    Si no tienes información específica, indícalo claramente.
    """


@router.post("/chat")
def chat(
        request: ChatRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        business_context = get_business_context(db)

        messages = [
            {"role": "system", "content": business_context},
            {"role": "user", "content": request.message}
        ]

        if request.context:
            messages.insert(1, {
                "role": "system",
                "content": f"Contexto adicional: {request.context}"
            })

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        return {
            "response": response.choices[0].message.content,
            "model": response.model,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error con Groq: {str(e)}")


@router.post("/analyze-prediction")
def analyze_prediction(
        unit_price: float,
        quantity: int,
        predicted_total: float,
        product_name: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        avg_price = db.query(func.avg(CompanyProductPrice.price)).scalar() or 0
        avg_total = db.query(func.avg(Purchase.total)).scalar() or 0

        prompt = f"""
        Se ha realizado una predicción de compra con estos datos:
        - Producto: {product_name}
        - Precio unitario: €{unit_price}
        - Cantidad: {quantity}
        - Total predicho: €{predicted_total:.2f}

        Datos del sistema para comparar:
        - Precio promedio histórico: €{float(avg_price):.2f}
        - Total promedio por compra: €{float(avg_total):.2f}

        Analiza si esta compra es normal, cara o barata comparada con el histórico.
        Da una recomendación concreta en 2-3 frases.
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system",
                 "content": "Eres un analista de negocios experto. Responde en español, de forma clara y directa."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.5,
        )

        return {
            "analysis": response.choices[0].message.content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error con Groq: {str(e)}")


@router.post("/analyze-segments")
def analyze_segments(
        vip_count: int,
        medio_count: int,
        dormido_count: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        total_revenue = db.query(func.sum(Purchase.total)).scalar() or 0
        total_customers = vip_count + medio_count + dormido_count

        prompt = f"""
        Segmentación de clientes del sistema:
        - Clientes VIP: {vip_count} ({round(vip_count / total_customers * 100)}%)
        - Clientes Medios: {medio_count} ({round(medio_count / total_customers * 100)}%)
        - Clientes Dormidos: {dormido_count} ({round(dormido_count / total_customers * 100)}%)
        - Ingresos totales: €{float(total_revenue):,.2f}

        Da 3 recomendaciones concretas de negocio basadas en esta segmentación.
        Sé específico y práctico.
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system",
                 "content": "Eres un consultor de negocios experto en retención de clientes. Responde en español."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.6,
        )

        return {
            "recommendations": response.choices[0].message.content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error con Groq: {str(e)}")