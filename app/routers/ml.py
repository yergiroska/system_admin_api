from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sqlalchemy import func
from app.auth import get_current_user
from app.models import User

from app.database import get_db
from app.models import Purchase, Customer, CompanyProductPrice, CompanyProduct, Product, Company

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"]
)


def get_trained_model(db: Session):
    purchases = db.query(Purchase).all()

    df = pd.DataFrame([{
        "unit_price": float(p.unit_price),
        "quantity": p.quantity,
        "product_id": p.company_product_id,
        "total": float(p.total),
    } for p in purchases])

    X = df[["unit_price", "quantity", "product_id"]]
    y = df["total"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    return model, mae, r2


class PredictRequest(BaseModel):
    unit_price: float
    quantity: int
    company_product_id: int


@router.get("/model-info")
def model_info(db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    model, mae, r2 = get_trained_model(db)
    return {
        "model": "Linear Regression",
        "features": ["unit_price", "quantity", "company_product_id"],
        "target": "total",
        "mae": round(mae, 2),
        "r2_score": round(r2, 4),
        "explanation": {
            "mae": f"El modelo se equivoca en promedio {round(mae, 2)}€ por compra",
            "r2": f"El modelo explica el {round(r2 * 100, 2)}% de la variación en los totales"
        }
    }


@router.post("/predict")
def predict_total(request: PredictRequest, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    model, mae, r2 = get_trained_model(db)

    input_data = pd.DataFrame([{
        "unit_price": request.unit_price,
        "quantity": request.quantity,
        "product_id": request.company_product_id,
    }])

    prediction = model.predict(input_data)[0]

    return {
        "input": {
            "unit_price": request.unit_price,
            "quantity": request.quantity,
            "company_product_id": request.company_product_id,
        },
        "predicted_total": round(float(prediction), 2),
        "model_mae": round(mae, 2),
    }

@router.get("/customer-segments")
def customer_segments(db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    results = (
        db.query(
            Customer.id,
            Customer.first_name,
            Customer.last_name,
            func.count(Purchase.id).label("total_purchases"),
            func.sum(Purchase.total).label("total_spent"),
            func.avg(Purchase.total).label("avg_order"),
        )
        .join(Purchase, Purchase.customer_id == Customer.id)
        .group_by(Customer.id, Customer.first_name, Customer.last_name)
        .all()
    )

    df = pd.DataFrame([{
        "id": r.id,
        "name": f"{r.first_name} {r.last_name}",
        "total_purchases": r.total_purchases,
        "total_spent": float(r.total_spent),
        "avg_order": float(r.avg_order),
    } for r in results])

    features = df[["total_purchases", "total_spent", "avg_order"]]
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(features_scaled)

    cluster_stats = df.groupby("cluster").agg(
        total_customers=("id", "count"),
        avg_purchases=("total_purchases", "mean"),
        avg_spent=("total_spent", "mean"),
        avg_order=("avg_order", "mean"),
    ).reset_index()

    labels = {}
    for _, row in cluster_stats.iterrows():
        if row["avg_spent"] == cluster_stats["avg_spent"].max():
            labels[row["cluster"]] = "VIP"
        elif row["avg_spent"] == cluster_stats["avg_spent"].min():
            labels[row["cluster"]] = "Dormido"
        else:
            labels[row["cluster"]] = "Medio"

    df["segment"] = df["cluster"].map(labels)

    segments = {}
    for segment in ["VIP", "Medio", "Dormido"]:
        group = df[df["segment"] == segment]
        segments[segment] = {
            "total_customers": len(group),
            "avg_purchases": round(group["total_purchases"].mean(), 1),
            "avg_spent": round(group["total_spent"].mean(), 2),
            "avg_order": round(group["avg_order"].mean(), 2),
            "customers": group[["id", "name", "total_purchases", "total_spent"]].to_dict(orient="records")
        }

    return segments

@router.get("/price-anomalies")
def price_anomalies(db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

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

    anomalies = df[df["anomaly"] == -1].copy()
    anomalies = anomalies.sort_values("score")

    total_prices = len(df)
    total_anomalies = len(anomalies)

    return {
        "summary": {
            "total_prices_analyzed": total_prices,
            "total_anomalies_found": total_anomalies,
            "anomaly_rate": f"{round(total_anomalies / total_prices * 100, 2)}%",
        },
        "anomalies": [
            {
                "id": int(row["id"]),
                "product": row["product_name"],
                "company": row["company_name"],
                "price": round(row["price"], 2),
                "anomaly_score": round(row["score"], 4),
                "date": row["date"],
            }
            for _, row in anomalies.iterrows()
        ]
    }