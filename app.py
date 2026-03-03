import os
import json
import traceback
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ============================
# CONFIGURACIÓN BASE DE DATOS
# ============================
# Local: SQLite (para pruebas). En Render/producción se recomienda PostgreSQL.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///whatbot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ============================
# MODELO: TABLA LOG DE ERRORES / EVENTOS
# ============================
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fech_y_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # UTC por defecto
    nivel = db.Column(db.String(10), nullable=False, default="INFO")              # INFO / WARNING / ERROR
    origen = db.Column(db.String(80), nullable=False, default="app")              # webhook-get / webhook-post / etc.
    texto = db.Column(db.Text, nullable=False)

# Crear la tabla si no existe
with app.app_context():
    db.create_all()

# ============================
# FUNCIONES AUXILIARES
# ============================
# Función para ordenar los registros de la tabla log por fecha y hora de forma descendente
def obtener_logs_ordenados():
    return Log.query.order_by(Log.fech_y_hora.desc()).all()

# Función para agregar un nuevo log y guardarlo en la base de datos
def agregar_mensaje_log(texto, nivel="INFO", origen="app"):
    # Asegurar que texto sea string (si llega dict/json, lo convertimos)
    if not isinstance(texto, str):
        texto = json.dumps(texto, ensure_ascii=False)

    nuevo_log = Log(texto=texto, nivel=nivel, origen=origen)
    db.session.add(nuevo_log)
    db.session.commit()

# ============================
# VISTA PRINCIPAL
# ============================
@app.route("/")
def index():
    # obtener todos los registros de la tabla log
    logs = obtener_logs_ordenados()
    return render_template("index.html", logs=logs)

# ============================
# WEBHOOK WHATSAPP
# ============================
# TOKEN DE VERIFICACION DE WHATBOT
# (Para producción, configúralo como variable de entorno en Render: VERIFY_TOKEN)
TOKEN_WHATBOT = os.environ.get("VERIFY_TOKEN", "whatbot_verify_2026")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    try:
        if request.method == "GET":
            # Verificación de webhook (Meta)
            return verificar_token(request)

        # POST: Meta enviará eventos aquí
        return recibir_mensaje(request)

    except Exception as e:
        # Capturar y registrar cualquier error real (con stacktrace)
        error_detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log(error_detalle, nivel="ERROR", origen="webhook-except")
        return jsonify({"error": "Internal Server Error"}), 500

def verificar_token(req):
    token = req.args.get("hub.verify_token")
    challenge = req.args.get("hub.challenge")

    if token == TOKEN_WHATBOT:
        agregar_mensaje_log("Webhook verificado correctamente", nivel="INFO", origen="webhook-get")
        return challenge, 200
    else:
        agregar_mensaje_log("Token de verificación no válido", nivel="ERROR", origen="webhook-get")
        return jsonify({"error": "Token de verificación no válido"}), 403

def recibir_mensaje(req):
    data = req.get_json(silent=True) or {}

    # Guardar el evento recibido (sirve como auditoría)
    agregar_mensaje_log(data, nivel="INFO", origen="webhook-post")

    # Aquí luego pondrás tu lógica de chatbot (responder, parsear, etc.)
    return jsonify({"message": "EVENT_RECEIVED"}), 200

# ============================
# EJECUCIÓN
# ============================
if __name__ == "__main__":
    # Render usa la variable PORT; local usará 3000
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)