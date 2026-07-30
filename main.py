import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def procesar():
    try:
        if request.method == 'GET':
            return jsonify({"status": "ok", "mensaje": "Servidor activo"}), 200

        # Leer JSON de forma segura sin romper el código si viene vacío
        data = request.get_json(silent=True) or {}
        
        return jsonify({
            "status": "success",
            "mensaje": "¡Conexión privada y segura 100% operativa!",
            "datos_recibidos": data
        }), 200

    except Exception as e:
        # Esto evita que devuelva 500 y en su lugar te da el detalle en el JSON
        return jsonify({"status": "error", "detalle": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)