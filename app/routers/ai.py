from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
import json
from groq import Groq
from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, Customer, CompanyProductPrice, ChatConversation
from app.auth import get_current_user
from app.models import User
import os
from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sentence_transformers import SentenceTransformer

load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"]
)

os.environ["OTEL_SDK_DISABLED"] = "true"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
def tool_top_products(db: Session, limit: int = 5, order_by: str = "quantity") -> str:
    order_col = func.sum(Purchase.quantity) if order_by == "quantity" else func.sum(Purchase.total)
    results = (
        db.query(Product.name, func.sum(Purchase.quantity).label("total_units"), func.sum(Purchase.total).label("total_revenue"))
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(order_col.desc())
        .limit(limit)
        .all()
    )
    rows = [f"- {r.name}: {int(r.total_units)} unidades · €{float(r.total_revenue):,.2f}" for r in results]
    return "Top productos:\n" + "\n".join(rows)


def tool_top_customers(db: Session, limit: int = 5, order_by: str = "total") -> str:
    order_col = func.sum(Purchase.total) if order_by == "total" else func.count(Purchase.id)
    results = (
        db.query(
            (Customer.first_name + " " + Customer.last_name).label("name"),
            func.sum(Purchase.total).label("total_spent"),
            func.count(Purchase.id).label("total_purchases")
        )
        .join(Purchase, Purchase.customer_id == Customer.id)
        .group_by(Customer.first_name, Customer.last_name)
        .order_by(order_col.desc())
        .limit(limit)
        .all()
    )
    rows = [f"- {r.name}: {int(r.total_purchases)} compras · €{float(r.total_spent):,.2f} gastado en total" for r in results]
    return "Top clientes:\n" + "\n".join(rows)


def tool_top_companies(db: Session, limit: int = 5, order_by: str = "total") -> str:
    order_col = func.sum(Purchase.total) if order_by == "total" else func.count(Purchase.id)
    results = (
        db.query(Company.name, func.sum(Purchase.total).label("total_revenue"), func.count(Purchase.id).label("total_purchases"))
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(order_col.desc())
        .limit(limit)
        .all()
    )
    rows = [f"- {r.name}: {int(r.total_purchases)} compras · €{float(r.total_revenue):,.2f}" for r in results]
    return "Top empresas:\n" + "\n".join(rows)


def tool_entity_detail(db: Session, entity_type: str, name: str) -> str:
    name_filter = f"%{name}%"

    if entity_type == "product":
        results = (
            db.query(Product.name, func.sum(Purchase.quantity).label("total_units"), func.sum(Purchase.total).label("total_revenue"), func.count(Purchase.id).label("total_purchases"))
            .join(CompanyProduct, CompanyProduct.product_id == Product.id)
            .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
            .filter(Product.name.ilike(name_filter))
            .group_by(Product.name)
            .first()
        )
        if not results:
            return f"No encontré ningún producto con el nombre '{name}'."
        return f"Producto '{results.name}': {int(results.total_units)} unidades vendidas · {int(results.total_purchases)} compras · €{float(results.total_revenue):,.2f} en ingresos"


    elif entity_type == "customer":
        results = (
            db.query(
                (Customer.first_name + " " + Customer.last_name).label("name"),
                func.sum(Purchase.total).label("total_spent"),
                func.count(Purchase.id).label("total_purchases")
            )
            .join(Purchase, Purchase.customer_id == Customer.id)
            .filter((Customer.first_name + " " + Customer.last_name).ilike(name_filter))
            .group_by(Customer.first_name, Customer.last_name)
            .first()
        )

        if not results:
            return f"No encontré ningún cliente con el nombre '{name}'."

        return f"Cliente '{results.name}': {int(results.total_purchases)} compras · €{float(results.total_spent):,.2f} gastado en total"

    elif entity_type == "company":
        results = (
            db.query(Company.name, func.sum(Purchase.total).label("total_revenue"), func.count(Purchase.id).label("total_purchases"))
            .join(CompanyProduct, CompanyProduct.company_id == Company.id)
            .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
            .filter(Company.name.ilike(name_filter))
            .group_by(Company.name)
            .first()
        )
        if not results:
            return f"No encontré ninguna empresa con el nombre '{name}'."
        return f"Empresa '{results.name}': {int(results.total_purchases)} compras · €{float(results.total_revenue):,.2f} en ingresos"

    return "Tipo de entidad no reconocido. Usa 'product', 'customer' o 'company'."


def tool_sales_summary(db: Session) -> str:
    total_purchases = db.query(func.count(Purchase.id)).scalar()
    total_revenue = db.query(func.sum(Purchase.total)).scalar() or 0
    total_customers = db.query(func.count(Customer.id)).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()
    return (
        f"Resumen general del negocio:\n"
        f"- Total compras: {total_purchases}\n"
        f"- Ingresos totales: €{float(total_revenue):,.2f}\n"
        f"- Clientes activos: {total_customers}\n"
        f"- Empresas: {total_companies}\n"
        f"- Productos: {total_products}"
    )

def save_message(db: Session, session_id: str, role: str, content: str):
    embedding = embedding_model.encode(content).tolist()
    msg = ChatConversation(
        session_id=session_id,
        role=role,
        content=content,
        embedding=embedding,
        created_at=func.now()
    )
    db.add(msg)
    db.commit()


def get_relevant_history(db: Session, session_id: str, query: str, limit: int = 5):
    query_embedding = embedding_model.encode(query).tolist()
    results = db.execute(
        text("""
            SELECT role, content
            FROM chat_conversations
            WHERE session_id = :session_id
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """),
        {
            "session_id": session_id,
            "embedding": str(query_embedding),
            "limit": limit
        }
    ).fetchall()
    return results

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    history: Optional[List[ChatMessage]] = []
    session_id: Optional[str] = "default"

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_top_products",
            "description": "Obtiene los productos más vendidos o con más ingresos",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Número de productos a retornar, por defecto 5"},
                    "order_by": {"type": "string", "enum": ["quantity", "total"], "description": "Ordenar por unidades vendidas o por ingresos"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_customers",
            "description": "Obtiene los clientes que más compran o más gastan, incluyendo número de compras Y monto total gastado en euros",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Número de clientes a retornar, por defecto 5"},
                    "order_by": {"type": "string", "enum": ["total", "count"], "description": "Ordenar por gasto total o por número de compras"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_companies",
            "description": "Obtiene las empresas con más ingresos o más compras",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Número de empresas a retornar, por defecto 5"},
                    "order_by": {"type": "string", "enum": ["total", "purchases"], "description": "Ordenar por ingresos o por número de compras"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_detail",
            "description": "Obtiene el detalle de un producto, cliente o empresa específico por nombre",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "enum": ["product", "customer", "company"], "description": "Tipo de entidad"},
                    "name": {"type": "string", "description": "Nombre o parte del nombre de la entidad"}
                },
                "required": ["entity_type", "name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Obtiene un resumen general del negocio: total compras, ingresos, clientes, empresas y productos",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

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
        session_id = f"user-{current_user.id}"
        system_prompt = """Eres un asistente de análisis de negocios para el sistema System Admin.
Tienes acceso a herramientas que consultan datos reales de la base de datos.
SIEMPRE usa las herramientas disponibles para responder preguntas sobre productos, clientes, empresas o ventas.
Responde siempre en español, de forma clara y concisa.
Nunca inventes datos — si no tienes información, usa una herramienta para obtenerla."""

        # Guardar mensaje del usuario
        save_message(db, session_id, "user", request.message)

        # Recuperar historial relevante por similitud semántica
        relevant_history = get_relevant_history(db, session_id, request.message)

        # Construir mensajes
        messages = [{"role": "system", "content": system_prompt}]

        for row in relevant_history:
            messages.append({"role": row.role, "content": row.content})

        # Añadir historial reciente del frontend
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": request.message})

        # Primera llamada a Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=GROQ_TOOLS,
            tool_choice="auto",
            max_tokens=1000,
            temperature=0.3,
        )

        response_message = response.choices[0].message

        if not response_message.tool_calls:
            content = response_message.content or ""
            if "<function=" in content:
                raise HTTPException(status_code=500, detail="Error: tool call inválida")
            save_message(db, session_id, "assistant", response_message.content)
            return {
                "response": response_message.content,
                "model": response.model,
            }

        messages.append({
            "role": "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in response_message.tool_calls
            ]
        })

        for tool_call in response_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            if "limit" in fn_args:
                fn_args["limit"] = int(fn_args["limit"])

            if fn_name == "get_top_products":
                result = tool_top_products(db, **fn_args)
            elif fn_name == "get_top_customers":
                result = tool_top_customers(db, **fn_args)
            elif fn_name == "get_top_companies":
                result = tool_top_companies(db, **fn_args)
            elif fn_name == "get_entity_detail":
                result = tool_entity_detail(db, **fn_args)
            elif fn_name == "get_sales_summary":
                result = tool_sales_summary(db)
            else:
                result = "Herramienta no reconocida."

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        final_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1000,
            temperature=0.3,
        )

        final_content = final_response.choices[0].message.content

        # Guardar respuesta del asistente
        save_message(db, session_id, "assistant", final_content)

        return {
            "response": final_content,
            "model": final_response.model,
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
            model="llama-3.3-70b-versatile",
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