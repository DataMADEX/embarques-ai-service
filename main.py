import os
import json
import base64
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Inicializar cliente de Gemini usando la clave de API desde variables de entorno
# Usa exactamente la variable configurada en Cloud Run: _GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("_GEMINI_API_KEY", "")

@app.route('/', methods=['POST', 'GET'])
def procesar_embarque():
    if request.method == 'GET':
        return jsonify({"status": "ok", "mensaje": "Servidor activo y listo para procesar PDFs"}), 200

    try:
        data = request.get_json(silent=True) or {}
        orden_compra = data.get("orden_compra", "N/A")
        pdf_base64 = data.get("pdf_base64", "")

        if not pdf_base64:
            return jsonify({
                "status": "error",
                "mensaje": "No se recibió el contenido del PDF en base64"
            }), 400

        if not GEMINI_API_KEY:
            return jsonify({
                "status": "error",
                "mensaje": "No se encontró la clave de Gemini en la variable _GEMINI_API_KEY"
            }), 500

        # Convertir Base64 a bytes de PDF
        pdf_bytes = base64.b64decode(pdf_base64)

        # 1. Preparar la llamada a la SDK de Gemini con el archivo adjunto
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Prompt estructurado exigiendo respuesta únicamente en JSON
        prompt = """
        Analiza el siguiente documento PDF de embarque/expediente y extrae la siguiente información estructurada:
        - numero_factura (string)
        - proveedor (string)
        - fecha_factura (string YYYY-MM-DD)
        - monto_total (float o number)
        - moneda (string, ej: USD, EUR)
        - resumen_mercancia (string breve con lo que se está transportando)

        Responde ÚNICAMENTE con un objeto JSON válido con estas claves exactas. No agregues texto adicional fuera del JSON.
        """

        # Pasar el PDF como parte del contenido multimodal
        part_pdf = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type="application/pdf"
        )

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[part_pdf, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # Parsear la respuesta de la IA
        datos_extraidos = json.loads(response.text)

        # Devolver el resultado formateado
        return jsonify({
            "status": "success",
            "orden_compra": orden_compra,
            "datos_ia": datos_extraidos
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "mensaje": f"Error al procesar con IA: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)