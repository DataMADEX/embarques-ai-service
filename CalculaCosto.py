import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def procesar():
    try:
        if request.method == 'GET':
            return jsonify({"status": "ok", "mensaje": "Servidor activo"}), 200
        
        data = request.get_json(silent=True) or {}
        nombre = data.get("nombre", "Usuario")

        return jsonify({
            "status": "success",
            "mensaje": f"¡Conexión privada exitosa, {nombre}!",
            "datos_recibidos": data
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)