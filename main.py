import os
import json
import base64
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/', methods=['POST', 'GET'])
def procesar_embarque():
    if request.method == 'GET':
        return jsonify({"status": "ok", "mensaje": "Servidor activo"}), 200

    try:
        data = request.get_json(silent=True) or {}
        orden_compra = data.get("orden_compra", "N/A")
        pdf_base64 = data.get("pdf_base64", "")

        if not pdf_base64:
            return jsonify({"status": "error", "mensaje": "No se recibió el PDF en base64"}), 400

        pdf_bytes = base64.b64decode(pdf_base64)
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Prompt optimizado para extraer MÚLTIPLES facturas del mismo expediente
        # Definir el esquema JSON estricto para forzar la respuesta esperada
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "facturas": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "numero_factura": {"type": "STRING"},
                            "proveedor": {"type": "STRING"},
                            "fecha_factura": {"type": "STRING"},
                            "monto_total": {"type": "NUMBER"},
                            "moneda": {"type": "STRING"},
                            "resumen_mercancia": {"type": "STRING"}
                        },
                        "required": ["numero_factura", "proveedor", "monto_total"]
                    }
                }
            },
            "required": ["facturas"]
        }

        prompt = """
        Lee minuciosamente este expediente de embarque de 9 páginas. 
        Extrae un desglose individual de CADA UNA de las facturas, comprobantes de pago de aduana/impuestos y facturas comerciales de 3M o fletes que encuentres.
        """

        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[part_pdf, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )

        part_pdf = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[part_pdf, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        datos_extraidos = json.loads(response.text)

        return jsonify({
            "status": "success",
            "orden_compra": orden_compra,
            "facturas": datos_extraidos.get("facturas", [])
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)