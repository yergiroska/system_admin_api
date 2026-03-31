import schedule
import time
import requests
from datetime import datetime


BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ── Tarea 1: Generar reporte PDF ───────────────────────
def generar_reporte():
    log("🔄 Iniciando generación de reporte PDF...")
    try:
        response = requests.get(f"{BASE_URL}/reports/sales-summary")
        if response.status_code == 200:
            filename = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            log(f"✅ Reporte guardado: {filename}")
        else:
            log(f"❌ Error generando reporte: {response.status_code}")
    except Exception as e:
        log(f"❌ Error: {e}")


# ── Tarea 2: Detectar anomalías ────────────────────────
# def detectar_anomalias():
#     log("🔄 Detectando anomalías de precios...")
#     try:
#         # Necesitamos token para endpoints protegidos
#         login = requests.post(f"{BASE_URL}/auth/login", data={
#             "username": "josefina@gmail.com",
#             "password": "123456"
#         })
#         token = login.json()["access_token"]
#
#         response = requests.get(
#             f"{BASE_URL}/ml/price-anomalies",
#             headers={"Authorization": f"Bearer {token}"}
#         )
#         if response.status_code == 200:
#             data = response.json()
#             total = data["summary"]["total_anomalies_found"]
#             rate = data["summary"]["anomaly_rate"]
#             log(f"✅ Anomalías detectadas: {total} ({rate})")
#
#             # Guardar resultado en archivo
#             filename = f"anomalias_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
#             with open(filename, 'w', encoding='utf-8') as f:
#                 f.write(f"Reporte de anomalías — {datetime.now()}\n")
#                 f.write(f"Total analizados: {data['summary']['total_prices_analyzed']}\n")
#                 f.write(f"Anomalías encontradas: {total} ({rate})\n\n")
#                 for a in data["anomalies"][:10]:
#                     f.write(f"  - {a['product']} | {a['company']} | €{a['price']}\n")
#             log(f"✅ Resultado guardado: {filename}")
#         else:
#             log(f"❌ Error: {response.status_code}")
#     except Exception as e:
#         log(f"❌ Error: {e}")

# Anomalias PDF
def detectar_anomalias():
    log("🔄 Detectando anomalías de precios...")
    try:
        response = requests.get(f"{BASE_URL}/reports/anomalies")
        if response.status_code == 200:
            filename = f"anomalias_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            log(f"✅ PDF de anomalías guardado: {filename}")
        else:
            log(f"❌ Error: {response.status_code}")
    except Exception as e:
        log(f"❌ Error: {e}")


# ── Tarea 3: Reentrenar modelo ML ──────────────────────
def reentrenar_modelo():
    log("🔄 Reentrenando modelo de regresión...")
    try:
        login = requests.post(f"{BASE_URL}/auth/login", data={
            "username": "josefina@gmail.com",
            "password": "123456"
        })
        token = login.json()["access_token"]

        response = requests.get(
            f"{BASE_URL}/ml/model-info",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Modelo reentrenado — R2: {data['r2_score']} | MAE: €{data['mae']}")
        else:
            log(f"❌ Error: {response.status_code}")
    except Exception as e:
        log(f"❌ Error: {e}")


# ── Tarea 4: Segmentar clientes ────────────────────────
def segmentar_clientes():
    log("🔄 Ejecutando segmentación de clientes...")
    try:
        login = requests.post(f"{BASE_URL}/auth/login", data={
            "username": "josefina@gmail.com",
            "password": "123456"
        })
        token = login.json()["access_token"]

        response = requests.get(
            f"{BASE_URL}/ml/customer-segments",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Segmentación completada:")
            log(f"   🟢 VIP:     {data['VIP']['total_customers']} clientes")
            log(f"   🟡 Medio:   {data['Medio']['total_customers']} clientes")
            log(f"   🔴 Dormido: {data['Dormido']['total_customers']} clientes")
        else:
            log(f"❌ Error: {response.status_code}")
    except Exception as e:
        log(f"❌ Error: {e}")


# ── Pipeline completo ──────────────────────────────────
def ejecutar_pipeline_completo():
    log("🚀 Iniciando pipeline completo...")
    generar_reporte()
    detectar_anomalias()
    reentrenar_modelo()
    segmentar_clientes()
    log("🎉 Pipeline completado!")
    print("─" * 50)


# ── Horarios (igual que Airflow DAGs) ─────────────────
schedule.every().day.at("02:00").do(generar_reporte)
schedule.every().day.at("03:00").do(detectar_anomalias)
schedule.every().monday.at("04:00").do(reentrenar_modelo)
schedule.every().day.at("05:00").do(segmentar_clientes)

# Para probar ahora mismo ejecuta el pipeline completo
if __name__ == "__main__":
    log("⚙️  Pipeline iniciado — esperando tareas programadas...")
    log("   Reporte PDF:      todos los días a las 02:00")
    log("   Anomalías:        todos los días a las 03:00")
    log("   Reentrenamiento:  todos los lunes a las 04:00")
    log("   Segmentación:     todos los días a las 05:00")
    print("─" * 50)

    # Ejecuta el pipeline ahora para probar
    ejecutar_pipeline_completo()

    # Luego queda escuchando el horario
    while True:
        schedule.run_pending()
        time.sleep(60)