import traceback
from flask import Blueprint, jsonify, render_template, request
from app.infraestructure.log_repository import agregar_mensaje_log, obtener_logs_ordenados
from app.application.procesar_mensaje import procesar_mensaje_texto

webhook_bp = Blueprint("webhook", __name__)

TOKEN_WHATBOT = "whatbot_verify_2026"

@webhook_bp.route("/")
def index():
    logs = obtener_logs_ordenados()
    return render_template("index.html", logs=logs)

@webhook_bp.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return verificar_token(request)
    return recibir_mensaje(request)

def verificar_token(req):
    token = req.args.get("hub.verify_token")
    challenge = req.args.get("hub.challenge")

    if token == TOKEN_WHATBOT:
        return challenge, 200

    agregar_mensaje_log({
        "numero": None,
        "tipo": "sistema",
        "texto": f"Token de verificación no válido. Token recibido: {token}"
    })
    return jsonify({"error": "Token de verificacion no válido"}), 403

def recibir_mensaje(req):
    try:
        data = req.get_json(silent=True)

        if data is None:
            agregar_mensaje_log({
                "numero": None,
                "tipo": "sistema",
                "texto": "Error: Body no es JSON válido o está vacío."
            })
            return jsonify({"error": "Invalid JSON"}), 400

        entry = (data.get("entry") or [{}])[0]
        change = (entry.get("changes") or [{}])[0]
        value = (change.get("value") or {})
        mensajes = value.get("messages", [])

        if not mensajes:
            return jsonify({"message": "EVENT_RECEIVED"}), 200

        message = mensajes[0]
        tipo = message.get("type")

        if tipo == "interactive":
            return jsonify({"message": "EVENT_RECEIVED"}), 200

        if tipo == "text":
            texto = (message.get("text") or {}).get("body", "")
            numero = message.get("from", "")

            procesar_mensaje_texto(numero, texto)

        return jsonify({"message": "EVENT_RECEIVED"}), 200

    except Exception as e:
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log({
            "numero": None,
            "tipo": "sistema",
            "texto": detalle
        })
        return jsonify({"error": "Internal Server Error"}), 500