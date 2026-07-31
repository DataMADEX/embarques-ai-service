from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.auth
import gspread
from datetime import datetime

app = FastAPI(title="Landed Cost Engine")

# Permisos requeridos para leer y escribir en Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_cliente_gspread():
    """Autenticación nativa para GCP Cloud Run usando ADC."""
    try:
        credentials, _ = google.auth.default(scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error autenticando credenciales de GCP: {str(e)}"
        )

class SolicitudLandedCost(BaseModel):
    id_spreadsheet: str

@app.get("/")
def estado():
    return {"status": "ok", "service": "Landed Cost API en Cloud Run"}

@app.post("/calcular-landed-cost")
def calcular_landed_cost(solicitud: SolicitudLandedCost):
    try:
        gc = obtener_cliente_gspread()
        libro = gc.open_by_key(solicitud.id_spreadsheet)
        
        # 1. Obtener lotes marcados como "Completo"
        hoja_lotes = libro.worksheet("Lotes")
        registros_lotes = hoja_lotes.get_all_records()
        
        lotes_completos = [
            str(r["Numero_Lote"]).strip() 
            for r in registros_lotes 
            if r.get("Completo") in [True, 1, "TRUE", "true"]
        ]
        
        if not lotes_completos:
            return {
                "status": "warning", 
                "message": "No hay lotes marcados como 'Completo' en la pestaña 'Lotes'."
            }

        # 2. Leer registros de Facturas_Base
        hoja_base = libro.worksheet("Facturas_Base")
        filas_base = hoja_base.get_all_records()

        datos_lotes = {}

        for fila in filas_base:
            lote = str(fila.get("Numero_Lote", "")).strip()

            if lote in lotes_completos:
                if lote not in datos_lotes:
                    datos_lotes[lote] = {
                        "materia_prima_total": 0.0,
                        "gastos_totales": 0.0,
                        "productos": []
                    }

                rubro = str(fila.get("Rubro", "")).strip().upper()
                monto_linea = float(fila.get("Monto_Linea", 0) or 0)
                precio_unitario = float(fila.get("Precio_Unitario", 0) or 0)
                cantidad = int(fila.get("Cantidad", 1) or 1)
                descripcion = str(fila.get("Descripcion", "N/A"))

                if rubro == "MATERIA_PRIMA":
                    datos_lotes[lote]["materia_prima_total"] += monto_linea
                    datos_lotes[lote]["productos"].append({
                        "descripcion": descripcion,
                        "cantidad": cantidad,
                        "precio_unitario": precio_unitario,
                        "monto_linea": monto_linea
                    })
                elif rubro in ["FLETE", "IMPUESTO", "MANEJO_LOCAL", "MANEJO_ORIGEN"]:
                    datos_lotes[lote]["gastos_totales"] += monto_linea

        # 3. Calcular prorrateo por ítem
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for lote, data in datos_lotes.items():
            mp_total = data["materia_prima_total"]
            gastos_totales = data["gastos_totales"]

            if mp_total <= 0:
                continue

            factor = gastos_totales / mp_total
            factor_porcentaje = f"{round(factor * 100, 2)}%"

            for prod in data["productos"]:
                costo_unitario_final = round(prod["precio_unitario"] * (1 + factor), 4)
                costo_total_linea = round(costo_unitario_final * prod["cantidad"], 2)

                resultados.append([
                    lote,
                    prod["descripcion"],
                    prod["cantidad"],
                    prod["precio_unitario"],
                    factor_porcentaje,
                    costo_unitario_final,
                    costo_total_linea,
                    fecha_actual
                ])

        # 4. Escribir en la hoja Calculo_Landed
        if resultados:
            try:
                hoja_calculo = libro.worksheet("Calculo_Landed")
            except gspread.exceptions.WorksheetNotFound:
                hoja_calculo = libro.add_worksheet(title="Calculo_Landed", rows="100", cols="8")
                hoja_calculo.append_row([
                    "Numero_Lote", "Descripcion_Producto", "Cantidad", "Precio_Unitario_Base",
                    "Factor_Landed (%)", "Costo_Unitario_Final", "Costo_Total_Linea", "Fecha_Calculo"
                ])

            hoja_calculo.resize(rows=1)
            hoja_calculo.resize(rows=len(resultados) + 1)
            hoja_calculo.append_rows(resultados)

            return {
                "status": "success",
                "lotes_procesados": len(lotes_completos),
                "filas_generadas": len(resultados)
            }

        return {"status": "info", "message": "No se encontraron productos de materia prima para procesar."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))