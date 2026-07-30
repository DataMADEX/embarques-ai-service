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
        prompt = """
        Analiza detenidamente este expediente PDF de embarque que contiene múltiples facturas y documentos de cobro.
        
        Extrae un listado JSON de TODAS las facturas o cobros individuales encontrados en el expediente.
        
        Devuelve un objeto JSON con una clave "facturas" que contenga una lista de objetos con esta estructura exacta:
        {
          "facturas": [
            {
              "numero_factura": "string",
              "proveedor": "string",
              "fecha_factura": "YYYY-MM-DD",
              "monto_total": number,
              "moneda": "USD o PAB",
              "resumen_mercancia": "string breve"
            }
          ]
        }

        Asegúrate de incluir las facturas de fletes/agencia de aduana y todas las facturas comerciales de mercancía.
        Responde ÚNICAMENTE con el objeto JSON válido.
        """

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