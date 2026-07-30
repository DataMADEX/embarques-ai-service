import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def procesar():
    try:
        # Recibir los datos enviados desde Google Apps Script
        data = request.get_json(silent=True) or {}
        
        nombre = data.get("nombre", "Usuario")
        
        return jsonify({
            "status": "success",
            "mensaje": f"¡Conexión exitosa desde Apps Script, {nombre}!",
            "datos_recibidos": data
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))