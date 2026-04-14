from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
import io

from app.database import get_db
from app.models import Purchase, CompanyProduct

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)


@router.get("/{purchase_id}")
def download_invoice(purchase_id: int, db: Session = Depends(get_db)):
    purchase = (
        db.query(Purchase)
        .options(
            joinedload(Purchase.customer),
            joinedload(Purchase.company_product).joinedload(CompanyProduct.company),
            joinedload(Purchase.company_product).joinedload(CompanyProduct.product),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

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

    # Encabezado
    elements.append(Paragraph("FACTURA", title_style))
    elements.append(Paragraph(f"Nº {purchase.id:06d}", subtitle_style))
    elements.append(Paragraph(
        f"Fecha: {purchase.created_at.strftime('%d/%m/%Y %H:%M')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    # Datos del cliente
    elements.append(Paragraph("Datos del cliente", section_style))
    customer_data = [
        ["Nombre", f"{purchase.customer.first_name} {purchase.customer.last_name or ''}"],
        ["Documento", purchase.customer.identity_document or "—"],
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

    # Detalle de la compra
    elements.append(Paragraph("Detalle de la compra", section_style))
    detail_data = [
        ["Producto", "Empresa", "Precio unit.", "Cantidad", "Total"],
        [
            purchase.company_product.product.name,
            purchase.company_product.company.name,
            f"€{float(purchase.unit_price):,.2f}",
            str(purchase.quantity),
            f"€{float(purchase.total):,.2f}",
        ]
    ]
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

    # Total final
    total_data = [["TOTAL A PAGAR", f"€{float(purchase.total):,.2f}"]]
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
        headers={"Content-Disposition": f"attachment; filename=factura_{purchase_id:06d}.pdf"}
    )