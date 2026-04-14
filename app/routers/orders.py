from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import io

from app.database import get_db
from app.models import Order, Purchase, CompanyProduct, Customer

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

@router.post("/")
def create_order(data: dict, db: Session = Depends(get_db)):
    customer_id = data.get("customer_id")
    items = data.get("items", [])

    if not items:
        raise HTTPException(status_code=400, detail="No hay productos en la orden")

    total = sum(item["unit_price"] * item["quantity"] for item in items)

    order = Order(
        customer_id=customer_id,
        total=total,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(order)
    db.flush()

    for item in items:
        purchase = Purchase(
            customer_id=customer_id,
            company_product_id=item["company_product_id"],
            unit_price=item["unit_price"],
            quantity=item["quantity"],
            total=item["unit_price"] * item["quantity"],
            order_id=order.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(purchase)

    db.commit()
    db.refresh(order)

    return {"order_id": order.id, "total": float(order.total)}

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.purchases)
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    return [
        {
            "id": o.id,
            "customer": f"{o.customer.first_name} {o.customer.last_name or ''}",
            "total_products": sum(p.quantity for p in o.purchases),
            "total": float(o.total),
            "created_at": o.created_at,
        }
        for o in orders
    ]

@router.get("/summary")
def get_orders_summary(db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.purchases)
        )
        .order_by(Order.created_at.desc())
        .all()
    )

    customer_map = {}
    for o in orders:
        cid = o.customer_id
        if cid not in customer_map:
            customer_map[cid] = {
                "customer": f"{o.customer.first_name} {o.customer.last_name or ''}",
                "total_products": 0,
                "total": 0.0,
                "last_order": o.created_at,
            }
        customer_map[cid]["total_products"] += sum(p.quantity for p in o.purchases)
        customer_map[cid]["total"] += float(o.total)
        if o.created_at > customer_map[cid]["last_order"]:
            customer_map[cid]["last_order"] = o.created_at

    return sorted(customer_map.values(), key=lambda x: x["total"], reverse=True)

@router.get("/customer/{customer_id}")
def get_orders_by_customer(customer_id: int, db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.purchases)
        )
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [
        {
            "id": o.id,
            "total_products": sum(p.quantity for p in o.purchases),
            "total": float(o.total),
            "created_at": o.created_at,
        }
        for o in orders
    ]

@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.purchases).joinedload(Purchase.company_product).joinedload(CompanyProduct.product),
            joinedload(Order.purchases).joinedload(Purchase.company_product).joinedload(CompanyProduct.company),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    return {
        "id": order.id,
        "customer": f"{order.customer.first_name} {order.customer.last_name or ''}",
        "total": float(order.total),
        "created_at": order.created_at,
        "items": [
            {
                "product": p.company_product.product.name,
                "company": p.company_product.company.name,
                "unit_price": float(p.unit_price),
                "quantity": p.quantity,
                "total": float(p.total),
            }
            for p in order.purchases
        ]
    }

@router.get("/{order_id}/invoice")
def order_invoice(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.purchases).joinedload(Purchase.company_product).joinedload(CompanyProduct.product),
            joinedload(Order.purchases).joinedload(Purchase.company_product).joinedload(CompanyProduct.company),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"],
        fontSize=20, textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER, spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER, spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#16213e"),
        spaceBefore=16, spaceAfter=8,
    )

    elements = []

    elements.append(Paragraph("FACTURA", title_style))
    elements.append(Paragraph(f"Orden N {order.id:06d}", subtitle_style))
    elements.append(Paragraph(
        f"Fecha: {order.created_at.strftime('%d/%m/%Y %H:%M')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph("Datos del cliente", section_style))
    customer_data = [
        ["Nombre", f"{order.customer.first_name} {order.customer.last_name or ''}"],
        ["Documento", order.customer.identity_document or "-"],
    ]
    customer_table = Table(customer_data, colWidths=[5*cm, 12*cm])
    customer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph("Detalle de la compra", section_style))
    detail_data = [["Producto", "Empresa", "Precio unit.", "Cantidad", "Total"]]
    for p in order.purchases:
        detail_data.append([
            p.company_product.product.name,
            p.company_product.company.name,
            f"€{float(p.unit_price):,.2f}",
            str(p.quantity),
            f"€{float(p.total):,.2f}",
        ])

    detail_table = Table(detail_data, colWidths=[5*cm, 5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 1*cm))

    total_data = [["TOTAL A PAGAR", f"€{float(order.total):,.2f}"]]
    total_table = Table(total_data, colWidths=[14*cm, 3.5*cm])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(total_table)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)
    doc.build(elements)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=factura_orden_{order_id:06d}.pdf"}
    )
