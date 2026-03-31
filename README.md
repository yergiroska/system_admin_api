# System Admin API

API REST de análisis de datos construida con FastAPI y PostgreSQL.

## Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Base de datos**: PostgreSQL
- **Data & ML**: Pandas, Matplotlib, Plotly, scikit-learn
- **Reportes**: ReportLab
- **Auth**: JWT

## Módulos

- CRUD: Empresas, Productos, Clientes, Compras
- Estadísticas y gráficas en tiempo real
- Reportes PDF automáticos
- Machine Learning: Regresión lineal, K-Means, IsolationForest
- Dashboard interactivo con Plotly
- Pipeline automatizado de tareas

## Instalación
```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Variables de entorno

Crea un archivo `.env` con:
```
DATABASE_URL=postgresql://user:password@localhost:5432/system_admin
```