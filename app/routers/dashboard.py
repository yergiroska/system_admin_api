from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

from app.database import get_db
from app.models import Purchase, CompanyProduct, Company, Product, CompanyProductPrice

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)):

    # ── Datos: ventas por empresa ──────────────────────────
    companies_data = (
        db.query(
            Company.name,
            func.sum(Purchase.total).label("total_sales"),
            func.count(Purchase.id).label("total_purchases")
        )
        .join(CompanyProduct, CompanyProduct.company_id == Company.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Company.name)
        .order_by(func.sum(Purchase.total).desc())
        .limit(10)
        .all()
    )

    # ── Datos: top productos ───────────────────────────────
    products_data = (
        db.query(
            Product.name,
            func.sum(Purchase.quantity).label("total_quantity"),
            func.sum(Purchase.total).label("total_sales")
        )
        .join(CompanyProduct, CompanyProduct.product_id == Product.id)
        .join(Purchase, Purchase.company_product_id == CompanyProduct.id)
        .group_by(Product.name)
        .order_by(func.sum(Purchase.quantity).desc())
        .limit(10)
        .all()
    )

    # ── Datos: compras por mes ─────────────────────────────
    monthly_data = (
        db.query(
            func.date_trunc('month', Purchase.created_at).label("month"),
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_sales")
        )
        .group_by(func.date_trunc('month', Purchase.created_at))
        .order_by(func.date_trunc('month', Purchase.created_at).asc())
        .all()
    )

    # ── Datos: distribución de precios ────────────────────
    prices_data = (
        db.query(CompanyProductPrice.price)
        .all()
    )
    prices = [float(p.price) for p in prices_data]

    # ── Gráfica 1: ventas por empresa (barras horizontales) ─
    fig1 = go.Figure(go.Bar(
        x=[float(r.total_sales) for r in companies_data],
        y=[r.name for r in companies_data],
        orientation='h',
        marker_color='#4f46e5',
        text=[f"€{float(r.total_sales):,.0f}" for r in companies_data],
        textposition='outside',
    ))
    fig1.update_layout(
        title="Top 10 empresas por ventas",
        xaxis_title="Ventas totales (€)",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    # ── Gráfica 2: top productos (barras verticales) ───────
    fig2 = go.Figure(go.Bar(
        x=[r.name for r in products_data],
        y=[int(r.total_quantity) for r in products_data],
        marker_color='#06b6d4',
        text=[str(int(r.total_quantity)) for r in products_data],
        textposition='outside',
    ))
    fig2.update_layout(
        title="Top 10 productos más vendidos",
        yaxis_title="Cantidad vendida",
        height=400,
        margin=dict(l=20, r=20, t=40, b=80),
        xaxis_tickangle=-45,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    # ── Gráfica 3: ventas por mes (línea con área) ─────────
    months = [r.month.strftime("%Y-%m") for r in monthly_data]
    sales = [float(r.total_sales) for r in monthly_data]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=months,
        y=sales,
        mode='lines+markers',
        fill='tozeroy',
        line=dict(color='#10b981', width=2),
        marker=dict(size=6),
        fillcolor='rgba(16, 185, 129, 0.1)',
    ))
    fig3.update_layout(
        title="Ventas por mes",
        yaxis_title="Ventas totales (€)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    # ── Gráfica 4: distribución de precios (histograma) ────
    fig4 = go.Figure(go.Histogram(
        x=prices,
        nbinsx=30,
        marker_color='#f59e0b',
        opacity=0.8,
    ))
    fig4.update_layout(
        title="Distribución de precios",
        xaxis_title="Precio (€)",
        yaxis_title="Frecuencia",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    # ── Métricas generales ─────────────────────────────────
    total_sales = db.query(func.sum(Purchase.total)).scalar() or 0
    total_purchases = db.query(func.count(Purchase.id)).scalar()
    total_customers = db.query(func.count(Purchase.customer_id.distinct())).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()

    # ── HTML ───────────────────────────────────────────────
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>System Admin Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; }}
            .header {{ background: #1e293b; color: white; padding: 20px 32px; display: flex; align-items: center; gap: 12px; }}
            .header h1 {{ font-size: 20px; font-weight: 600; }}
            .header span {{ font-size: 13px; color: #94a3b8; }}
            .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px 32px 0; }}
            .metric {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
            .metric .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
            .metric .value {{ font-size: 28px; font-weight: 700; color: #1e293b; }}
            .metric .sub {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
            .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 24px 32px; }}
            .chart-full {{ grid-column: 1 / -1; }}
            .chart-card {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
            .metric.blue .value {{ color: #4f46e5; }}
            .metric.cyan .value {{ color: #06b6d4; }}
            .metric.green .value {{ color: #10b981; }}
            .metric.amber .value {{ color: #f59e0b; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>System Admin Dashboard Compra</h1>
                <span>Análisis de ventas en tiempo real</span>
            </div>
        </div>

        <div class="metrics">
            <div class="metric blue">
                <div class="label">Ingresos totales</div>
                <div class="value">€{float(total_sales):,.0f}</div>
                <div class="sub">Todas las compras</div>
            </div>
            <div class="metric cyan">
                <div class="label">Total compras</div>
                <div class="value">{total_purchases}</div>
                <div class="sub">Transacciones</div>
            </div>
            <div class="metric green">
                <div class="label">Clientes activos</div>
                <div class="value">{total_customers}</div>
                <div class="sub">Con al menos 1 compra</div>
            </div>
            <div class="metric amber">
                <div class="label">Empresas</div>
                <div class="value">{total_companies}</div>
                <div class="sub">Proveedores activos</div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-card chart-full">
                <div id="chart3"></div>
            </div>
            <div class="chart-card">
                <div id="chart1"></div>
            </div>
            <div class="chart-card">
                <div id="chart2"></div>
            </div>
            <div class="chart-card chart-full">
                <div id="chart4"></div>
            </div>
        </div>

        <script>
            Plotly.newPlot('chart1', {json.dumps(fig1.to_dict()['data'])}, {json.dumps(fig1.to_dict()['layout'])}, {{responsive: true}});
            Plotly.newPlot('chart2', {json.dumps(fig2.to_dict()['data'])}, {json.dumps(fig2.to_dict()['layout'])}, {{responsive: true}});
            Plotly.newPlot('chart3', {json.dumps(fig3.to_dict()['data'])}, {json.dumps(fig3.to_dict()['layout'])}, {{responsive: true}});
            Plotly.newPlot('chart4', {json.dumps(fig4.to_dict()['data'])}, {json.dumps(fig4.to_dict()['layout'])}, {{responsive: true}});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)