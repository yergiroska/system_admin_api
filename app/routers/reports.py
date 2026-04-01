from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, Customer

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


def build_pdf(elements):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    doc.build(elements)
    buf.seek(0)
    return buf


def get_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#16213e"),
        spaceBefore=16,
        spaceAfter=8,
    )
    return title_style, subtitle_style, section_style


@router.get("/sales-summary")
def report_sales_summary(db: Session = Depends(get_db)):
    title_style, subtitle_style, section_style = get_styles()
    elements = []

    # Encabezado
    elements.append(Paragraph("Reporte de Ventas", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Resumen general
    total_purchases = db.query(func.count(Purchase.id)).scalar()
    total_revenue = db.query(func.sum(Purchase.total)).scalar() or 0
    total_customers = db.query(func.count(Customer.id)).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()

    elements.append(Paragraph("Resumen general", section_style))

    summary_data = [
        ["Métrica", "Valor"],
        ["Total de compras", str(total_purchases)],
        ["Ingresos totales", f"{float(total_revenue):,.2f}€"],
        ["Total de clientes", str(total_customers)],
        ["Total de empresas", str(total_companies)],
    ]

    summary_table = Table(summary_data, colWidths=[9*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    # Top empresas
    elements.append(Paragraph("Top 10 empresas por ventas", section_style))

    company_results = (
        db.query(
            Company.name,
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_sales")
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .limit(15)
        .all()
    )

    company_data = [["#", "Empresa", "Compras", "Ventas totales"]]
    for i, r in enumerate(company_results, 1):
        company_data.append([
            str(i),
            r.name,
            str(r.total_purchases),
            f"{float(r.total_sales):,.2f}€"
        ])

    company_table = Table(company_data, colWidths=[1*cm, 10*cm, 3*cm, 4*cm], repeatRows=1, splitByRow=1)
    company_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(company_table)
    elements.append(Spacer(1, 0.5*cm))

    # Top productos
    elements.append(Paragraph("Top 10 productos más vendidos", section_style))

    product_results = (
        db.query(
            Product.name,
            func.sum(Purchase.quantity).label("total_quantity"),
            func.sum(Purchase.total).label("total_sales")
        )
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(func.sum(Purchase.quantity).desc())
        .limit(15)
        .all()
    )

    product_data = [["#", "Producto", "Cantidad vendida", "Ventas totales"]]
    for i, r in enumerate(product_results, 1):
        product_data.append([
            str(i),
            r.name,
            str(int(r.total_quantity)),
            f"{float(r.total_sales):,.2f}€"
        ])

    product_table = Table(product_data, colWidths=[1*cm, 10*cm, 3.5*cm, 3.5*cm], repeatRows=1, splitByRow=1)
    product_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(product_table)

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_ventas.pdf"}
    )

@router.get("/top-customers")
def report_top_customers(db: Session = Depends(get_db)):
    title_style, subtitle_style, section_style = get_styles()
    elements = []

    elements.append(Paragraph("Top 10 Clientes VIP", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    results = (
        db.query(
            Customer.first_name,
            Customer.last_name,
            Customer.identity_document,
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_spent"),
            func.avg(Purchase.total).label("avg_order"),
        )
        .join(Purchase, Purchase.customer_id == Customer.id)
        .filter(Customer.deleted_at.is_(None))
        .group_by(Customer.id, Customer.first_name, Customer.last_name, Customer.identity_document)
        .order_by(func.sum(Purchase.total).desc())
        .limit(10)
        .all()
    )

    elements.append(Paragraph("Top 10 clientes por volumen de compras", section_style))

    data = [["#", "Cliente", "Documento", "Compras", "Total gastado", "Ticket medio"]]
    for i, r in enumerate(results, 1):
        data.append([
            str(i),
            f"{r.first_name} {r.last_name}",
            r.identity_document or "—",
            str(r.total_purchases),
            f"€{float(r.total_spent):,.2f}",
            f"€{float(r.avg_order):,.2f}",
        ])

    table = Table(data, colWidths=[1*cm, 5*cm, 3*cm, 2*cm, 3.5*cm, 3.5*cm], repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (2, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(table)

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_top_clientes.pdf"}
    )

@router.get("/anomalies")
def report_anomalies(db: Session = Depends(get_db)):
    from sklearn.ensemble import IsolationForest
    from app.models import CompanyProductPrice, CompanyProduct, Product, Company
    import pandas as pd

    title_style, subtitle_style, section_style = get_styles()
    elements = []

    # Encabezado
    elements.append(Paragraph("Reporte de Anomalías de Precios", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Obtener datos
    results = (
        db.query(
            CompanyProductPrice.id,
            CompanyProductPrice.price,
            CompanyProductPrice.created_at,
            CompanyProduct.product_id,
            CompanyProduct.company_id,
            Product.name.label("product_name"),
            Company.name.label("company_name"),
        )
        .join(CompanyProduct, CompanyProduct.id == CompanyProductPrice.company_product_id)
        .join(Product, Product.id == CompanyProduct.product_id)
        .join(Company, Company.id == CompanyProduct.company_id)
        .all()
    )

    df = pd.DataFrame([{
        "id": r.id,
        "price": float(r.price),
        "product_id": r.product_id,
        "company_id": r.company_id,
        "product_name": r.product_name,
        "company_name": r.company_name,
        "date": r.created_at,
    } for r in results])

    features = df[["price", "product_id", "company_id"]]
    model = IsolationForest(contamination=0.05, random_state=42)
    df["anomaly"] = model.fit_predict(features)
    df["score"] = model.decision_function(features)
    anomalies = df[df["anomaly"] == -1].sort_values("score")

    total = len(anomalies)
    rate = round(total / len(df) * 100, 2)

    # Resumen
    elements.append(Paragraph("Resumen", section_style))
    summary_data = [
        ["Métrica", "Valor"],
        ["Total precios analizados", str(len(df))],
        ["Anomalías encontradas", str(total)],
        ["Tasa de anomalías", f"{rate}%"],
    ]
    summary_table = Table(summary_data, colWidths=[9*cm, 8*cm], repeatRows=1, splitByRow=1)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    # Detalle
    elements.append(Paragraph("Detalle de anomalías detectadas", section_style))
    anomaly_data = [["#", "Producto", "Empresa", "Precio", "Score", "Fecha"]]
    for i, (_, row) in enumerate(anomalies.iterrows(), 1):
        fecha = row["date"].strftime("%Y-%m-%d") if row["date"] else "—"
        anomaly_data.append([
            str(i),
            row["product_name"],
            row["company_name"][:20],
            f"€{round(row['price'], 2)}",
            str(round(row["score"], 4)),
            fecha,
        ])

    anomaly_table = Table(anomaly_data, colWidths=[1*cm, 4*cm, 5*cm, 2*cm, 2.5*cm, 2.5*cm], repeatRows=1, splitByRow=1)
    anomaly_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (2, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(anomaly_table)

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_anomalias.pdf"}
    )

@router.get("/dormant-products")
def report_dormant_products(db: Session = Depends(get_db)):
    from app.models import Product, CompanyProduct, Purchase

    title_style, subtitle_style, section_style = get_styles()
    elements = []

    elements.append(Paragraph("Productos sin movimiento", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Productos que no tienen ninguna compra
    subquery = db.query(CompanyProduct.product_id).join(
        Purchase, Purchase.company_product_id == CompanyProduct.id
    ).subquery()

    results = (
        db.query(Product)
        .filter(
            Product.deleted_at.is_(None),
            ~Product.id.in_(subquery)
        )
        .all()
    )

    elements.append(Paragraph(f"Productos sin compras registradas: {len(results)}", section_style))

    if results:
        data = [["#", "Producto", "Descripción", "Creado"]]
        for i, r in enumerate(results, 1):
            data.append([
                str(i),
                r.name,
                r.description or "—",
                r.created_at.strftime("%d/%m/%Y") if r.created_at else "—",
            ])

        table = Table(data, colWidths=[1*cm, 4*cm, 8*cm, 3*cm], repeatRows=1, splitByRow=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (2, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Todos los productos tienen compras registradas.", section_style))

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_productos_dormidos.pdf"}
    )

@router.get("/monthly-summary")
def report_monthly_summary(db: Session = Depends(get_db)):
    title_style, subtitle_style, section_style = get_styles()
    elements = []

    elements.append(Paragraph("Resumen mensual por empresa", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    results = (
        db.query(
            Company.name.label("company_name"),
            func.date_trunc('month', Purchase.created_at).label("month"),
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_sales"),
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name, func.date_trunc('month', Purchase.created_at))
        .order_by(Company.name, func.date_trunc('month', Purchase.created_at))
        .all()
    )

    # Agrupar por empresa
    from collections import defaultdict
    company_data = defaultdict(list)
    for r in results:
        company_data[r.company_name].append(r)

    for company_name, rows in company_data.items():
        elements.append(Paragraph(company_name, section_style))

        data = [["Mes", "Compras", "Ventas totales"]]
        total_sales = 0
        total_purchases = 0
        for r in rows:
            data.append([
                r.month.strftime("%Y-%m"),
                str(r.total_purchases),
                f"€{float(r.total_sales):,.2f}",
            ])
            total_sales += float(r.total_sales)
            total_purchases += r.total_purchases

        data.append(["TOTAL", str(total_purchases), f"€{total_sales:,.2f}"])

        table = Table(data, colWidths=[6*cm, 4*cm, 7*cm], repeatRows=1, splitByRow=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f8f9fa"), colors.white]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*cm))

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_mensual_empresas.pdf"}
    )

@router.get("/sales-by-date")
def report_sales_by_date(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    from datetime import datetime as dt

    title_style, subtitle_style, section_style = get_styles()
    elements = []

    try:
        start = dt.strptime(start_date, "%Y-%m-%d")
        end = dt.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Formato de fecha incorrecto. Usa YYYY-MM-DD")

    elements.append(Paragraph("Reporte de ventas por período", title_style))
    elements.append(Paragraph(f"Generado el {dt.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Paragraph(f"Período: {start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))

    # Resumen general del período
    total_purchases = db.query(func.count(Purchase.id)).filter(
        Purchase.created_at >= start,
        Purchase.created_at <= end
    ).scalar()

    total_revenue = db.query(func.sum(Purchase.total)).filter(
        Purchase.created_at >= start,
        Purchase.created_at <= end
    ).scalar() or 0

    elements.append(Paragraph("Resumen del período", section_style))
    summary_data = [
        ["Métrica", "Valor"],
        ["Total de compras", str(total_purchases)],
        ["Ingresos totales", f"€{float(total_revenue):,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[9*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    # Ventas por empresa en el período
    company_results = (
        db.query(
            Company.name,
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_sales"),
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .filter(
            Purchase.created_at >= start,
            Purchase.created_at <= end
        )
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .all()
    )

    elements.append(Paragraph("Ventas por empresa en el período", section_style))
    company_data = [["#", "Empresa", "Compras", "Ventas totales"]]
    for i, r in enumerate(company_results, 1):
        company_data.append([
            str(i),
            r.name,
            str(r.total_purchases),
            f"€{float(r.total_sales):,.2f}",
        ])

    company_table = Table(company_data, colWidths=[1*cm, 10*cm, 3*cm, 4*cm], repeatRows=1, splitByRow=1)
    company_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(company_table)

    buf = build_pdf(elements)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_ventas_periodo.pdf"}
    )