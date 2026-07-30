import functions_framework
import json
import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

@functions_framework.http
def procesar_embarque_3m(request):
    try:
        request_json = request.get_json(silent=True)
        if not request_json or 'pdf_base64' not in request_json:
            return json.dumps({"error": "Payload JSON inválido. Se requiere 'pdf_base64'"}), 400

        orden_compra = request_json.get("orden_compra", "DESCONOCIDA")
        pdf_base64 = request_json.get("pdf_base64")

        # Inicializar modelo Gemini (soporta PDFs de múltiples páginas)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prompt consolidado para extraer TODO en un solo paso
        prompt = """
        Este PDF contiene un expediente completo de importación con varias páginas.
        Analiza todo el documento y extrae la información en un formato JSON estricto con la siguiente estructura:

        {
          "facturas_materia_prima": [
            {
              "factura_nbr": "string",
              "monto_total": float,
              "items": [
                {
                  "3m_id": "string",
                  "descripcion": "string",
                  "cantidad": float,
                  "precio_unitario": float,
                  "monto_linea": float
                }
              ]
            }
          ],
          "gastos_flete_transporte": [
            {
              "proveedor": "string",
              "monto": float
            }
          ],
          "impuestos_aduana": [
            {
              "documento": "string",
              "monto": float
            }
          ]
        }

        Instrucciones estrictas:
        - Identifica todas las facturas de 3M (Commercial Invoice / Global Channel Services) y extrae sus ítems.
        - Identifica la factura de flete/logística (ej. AMAD LOGISTICS) y extrae su costo total de servicio.
        - Identifica la liquidación o boleta de pago de aduana y extrae el total de impuestos a pagar.
        - Responde ÚNICAMENTE con el objeto JSON estricto sin markdown.
        """

        pdf_blob = {"mime_type": "application/pdf", "data": pdf_base64}
        response = model.generate_content([prompt, pdf_blob])
        
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        data_extracted = json.loads(raw_text)

        # 1. ACUMULAR ÍTEMS Y GASTOS
        materia_prima_items = []
        for factura in data_extracted.get("facturas_materia_prima", []):
            for item in factura.get("items", []):
                materia_prima_items.append({
                    "factura_origen": factura.get("factura_nbr"),
                    "3m_id": item.get("3m_id"),
                    "descripcion": item.get("descripcion"),
                    "cantidad": float(item.get("cantidad", 1)),
                    "costo_base_unitario": float(item.get("precio_unitario", 0)),
                    "monto_linea_base": float(item.get("monto_linea", 0))
                })

        gastos_flete_total = sum(float(f.get("monto", 0)) for f in data_extracted.get("gastos_flete_transporte", []))
        gastos_aduana_total = sum(float(a.get("monto", 0)) for a in data_extracted.get("impuestos_aduana", []))

        # 2. CÁLCULO DE LANDED COST
        monto_total_materia_prima = sum(item["monto_linea_base"] for item in materia_prima_items)

        if monto_total_materia_prima == 0:
            return json.dumps({"error": "No se encontraron ítems válidos de materia prima en el PDF."}), 400

        total_gastos_adicionales = gastos_flete_total + gastos_aduana_total
        factor_recargo = total_gastos_adicionales / monto_total_materia_prima

        # 3. RECALCULAR COSTOS UNITARIOS
        items_calculados = []
        for item in materia_prima_items:
            costo_base = item["costo_base_unitario"]
            costo_landed_unitario = round(costo_base * (1 + factor_recargo), 4)
            monto_linea_landed = round(item["cantidad"] * costo_landed_unitario, 2)

            items_calculados.append({
                "3m_id": item["3m_id"],
                "descripcion": item["descripcion"],
                "cantidad": item["cantidad"],
                "costo_base_unitario": costo_base,
                "costo_landed_unitario": costo_landed_unitario, # <--- VALOR FINAL A ZOHO
                "monto_linea_landed": monto_linea_landed
            })

        resultado_final = {
            "orden_compra": orden_compra,
            "resumen_costos": {
                "monto_materia_prima_fob": round(monto_total_materia_prima, 2),
                "gastos_flete": round(gastos_flete_total, 2),
                "gastos_aduana": round(gastos_aduana_total, 2),
                "total_gastos_extras": round(total_gastos_adicionales, 2),
                "factor_recargo_porcentaje": f"{round(factor_recargo * 100, 2)}%"
            },
            "productos_recalculados": items_calculados
        }

        return (json.dumps(resultado_final, ensure_ascii=False), 200, {'Content-Type': 'application/json'})

    except Exception as e:
        return json.dumps({"error": f"Error procesando el archivo único: {str(e)}"}), 500