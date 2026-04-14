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
        company_product_id: int,
        mae: float,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        product_name = (
            db.query(Product.name)
            .join(CompanyProduct, CompanyProduct.product_id == Product.id)
            .filter(CompanyProduct.id == company_product_id)
            .scalar() or "Desconocido"
        )

        avg_price = (
            db.query(func.avg(CompanyProductPrice.price))
            .filter(CompanyProductPrice.company_product_id == company_product_id)
            .scalar() or 0
        )

        avg_quantity = (
            db.query(func.avg(Purchase.quantity))
            .filter(Purchase.company_product_id == company_product_id)
            .scalar() or 0
        )

        diff_price_pct = ((unit_price - float(avg_price)) / float(avg_price) * 100) if avg_price else 0
        diff_quantity_pct = ((quantity - float(avg_quantity)) / float(avg_quantity) * 100) if avg_quantity else 0
        diff_abs = abs(quantity - float(avg_quantity))

        # Status de precio
        precio_status = "NORMAL"
        if diff_price_pct > 30:
            precio_status = "CARO"
        elif diff_price_pct > 10:
            precio_status = "LIGERAMENTE ELEVADO"
        elif diff_price_pct < -40:
            precio_status = "POSIBLE FRAUDE"
        elif diff_price_pct < -10:
            precio_status = "BARATO"

        # Status de cantidad
        cantidad_status = "NORMAL"
        if diff_abs > 10 and diff_quantity_pct > 50:
            cantidad_status = "INUSUALMENTE ALTA"

        # Status de fiabilidad
        fiabilidad_status = "FIABLE"
        if mae / predicted_total * 100 > 30:
            fiabilidad_status = "POCO FIABLE"

        # Textos construidos en Python
        if precio_status == "NORMAL":
            if abs(diff_price_pct) < 2:
                precio_info = f"El precio de €{unit_price} es prácticamente idéntico al histórico de €{float(avg_price):.2f} (diferencia de {diff_price_pct:+.1f}%)"
            else:
                precio_info = f"El precio de €{unit_price} es normal respecto al histórico de €{float(avg_price):.2f} ({diff_price_pct:+.1f}%)"
        elif precio_status == "CARO":
            precio_info = f"El precio de €{unit_price} es caro, un {diff_price_pct:.1f}% por encima del histórico de €{float(avg_price):.2f}"
        elif precio_status == "LIGERAMENTE ELEVADO":
            precio_info = f"El precio de €{unit_price} está ligeramente elevado, un {diff_price_pct:.1f}% sobre el histórico de €{float(avg_price):.2f}"
        elif precio_status == "BARATO":
            precio_info = f"El precio de €{unit_price} es bajo, un {abs(diff_price_pct):.1f}% por debajo del histórico de €{float(avg_price):.2f}"
        else:
            precio_info = f"El precio de €{unit_price} es un {abs(diff_price_pct):.1f}% inferior al histórico de €{float(avg_price):.2f}, puede indicar fraude o calidad comprometida"

        if cantidad_status == "INUSUALMENTE ALTA":
            cantidad_info = f"La cantidad de {quantity} unidades supera en {diff_abs:.0f} unidades el histórico de {float(avg_quantity):.0f} unidades"
        else:
            cantidad_info = f"La cantidad de {quantity} unidades es normal respecto al histórico de {float(avg_quantity):.0f} unidades"

        fiabilidad_status = "FIABLE"
        if mae / predicted_total * 100 > 30:
            fiabilidad_status = "POCO FIABLE"

        if fiabilidad_status == "POCO FIABLE":
            fiabilidad_info = "La predicción tiene un margen de error elevado, tómala con cautela"
        else:
            fiabilidad_info = "La predicción del modelo es matemáticamente fiable"

        prompt = f"""
        Redacta un análisis de compra para el responsable de compras con exactamente 3 punto:

        1. PRECIO: {precio_info}. Explica si debe preocuparse o no y por qué.
        2. CANTIDAD: {cantidad_info}. Explica si tiene sentido para el negocio o si debe revisarlo.
        3. FIABILIDAD: {fiabilidad_info}. Explica qué significa esto para la decisión de compra.

        No cambies los números. Sé específico y útil para alguien que va a tomar una decisión de compra ahora mismo.
        """

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": """Eres un asistente de análisis de compras para una plataforma de gestión empresarial B2B.
                    Usa únicamente los datos proporcionados, sin calcular ni inferir valores no presentes.
                    Si los datos son insuficientes, indícalo claramente.
                    Responde en español, de forma concisa y profesional."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3,
        )

        return {"analysis": response.choices[0].message.content}

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