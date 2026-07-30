import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def procesar():
    data = request.get_json()
    # Aquí irá tu lógica para leer el PDF o llamar a Gemini
    return jsonify({"status": "ok", "mensaje": "Servidor funcionando correctamente!"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))