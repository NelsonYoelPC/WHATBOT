from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import traceback
import http.client
import os
from pypdf import PdfReader
from openai import OpenAI
from whatsapp_service import enviar_mensajes
app = Flask(__name__)

# =========================
# Configuración SQLAlchemy
# =========================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# =========================
# Modelo: Log
# =========================
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fech_y_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    texto = db.Column(db.Text, nullable=False)


# Crear la tabla si no existe
with app.app_context():
    db.create_all()


# Función para ordenar los registros de la tabla log por fecha y hora de forma descendente
def obtener_logs_ordenados():
    return Log.query.order_by(Log.fech_y_hora.desc()).all()


@app.route('/')
def index():
    logs = obtener_logs_ordenados()
    return render_template('index.html', logs=logs)


# Función para agregar un nuevo mensaje y guardarlo en la base de datos
def agregar_mensaje_log(texto):
    # Asegura que lo que guardas en texto sea string
    if not isinstance(texto, str):
        texto = json.dumps(texto, ensure_ascii=False)

    nuevo_log = Log(texto=texto)
    db.session.add(nuevo_log)
    db.session.commit()


# =========================
# Webhook WhatsApp (Meta)
# =========================

# TOKEN DE VERIFICACION DE WHATBOT
TOKEN_WHATBOT = 'whatbot_verify_2026'


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verificar_token(request)
    else:
        return recibir_mensaje(request)


def verificar_token(req):
    token = req.args.get('hub.verify_token')
    challenge = req.args.get('hub.challenge')

    if token == TOKEN_WHATBOT:
        return challenge, 200

    # Registrar SOLO el error (token inválido)
    agregar_mensaje_log({
        "error": "Token de verificación no válido",
        "token_recibido": token
    })
    return jsonify({'error': 'Token de verificacion no válido'}), 403

def recibir_mensaje(req):
    try:
        data = req.get_json(silent=True)

        if data is None:
            agregar_mensaje_log("Error: Body no es JSON válido o está vacío.")
            return jsonify({'error': 'Invalid JSON'}), 400

        entry = (data.get("entry") or [{}])[0]
        change = (entry.get("changes") or [{}])[0]
        value = (change.get("value") or {})

        # A veces Meta manda eventos sin "messages" (por ejemplo statuses)
        mensaje = value.get("messages", [])

        # Si NO hay mensajes, no guardamos nada (no es error)
        if not mensaje:
            return jsonify({'message': 'EVENT_RECEIVED'}), 200

        messages = mensaje[0]
        tipo = messages.get("type")

        if tipo == "interactive":
            return jsonify({'message': 'EVENT_RECEIVED'}), 200

        if tipo == "text":
            texto = (messages.get("text") or {}).get("body", "")
            numero = messages.get("from", "")

            agregar_mensaje_log(json.dumps({
                "numero": numero,
                "tipo": tipo,
                "texto": texto
            }, ensure_ascii=False))

            ##respuesta = generar_respuesta_desde_pdf(texto)
            enviar_mensajes(texto, numero, agregar_mensaje_log)

        return jsonify({'message': 'EVENT_RECEIVED'}), 200

    except Exception as e:
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log(detalle)
        return jsonify({'error': 'Internal Server Error'}), 500


# =========================
# OpenAI + PDF
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PDF_PATH = os.environ.get("PDF_PATH", "Docs/catalogo.pdf")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
_pdf_text_cache = None

def cargar_texto_pdf():
    global _pdf_text_cache
    if _pdf_text_cache is not None:
        return _pdf_text_cache

    if not os.path.exists(PDF_PATH):
        agregar_mensaje_log(f"ERROR: No existe el PDF en la ruta: {PDF_PATH}")
        _pdf_text_cache = ""
        return _pdf_text_cache

    reader = PdfReader(PDF_PATH)
    parts = []
    for i, page in enumerate(reader.pages):
        t = (page.extract_text() or "").strip()
        if t:
            parts.append(f"[Página {i+1}]\n{t}")

    _pdf_text_cache = "\n\n".join(parts)
    return _pdf_text_cache

def buscar_fragmentos(pdf_text: str, pregunta: str, max_chars: int = 3500):
    """
    Búsqueda simple: toma palabras clave y recupera líneas que las contengan.
    """
    q = (pregunta or "").lower()
    palabras = [p for p in q.replace("¿", " ").replace("?", " ").split() if len(p) >= 4]

    lineas = [ln.strip() for ln in pdf_text.splitlines() if ln.strip()]
    encontrados = []

    for ln in lineas:
        lnl = ln.lower()
        if any(p in lnl for p in palabras):
            encontrados.append(ln)

    # Reduce tamaño (para no pasar demasiado al modelo)
    texto = "\n".join(encontrados)
    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n...[recortado]..."
    return texto

def generar_respuesta_desde_pdf(texto_usuario: str) -> str:
    t = (texto_usuario or "").strip()

    # Saludo natural (sin depender del PDF)
    if t.lower() in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"]:
        return "Hola, bienvenido(a) a nuestra inmobiliaria. ¿Deseas comprar, vender o alquilar una propiedad?"

    pdf_text = cargar_texto_pdf()
    if not pdf_text:
        return "No pude leer el catálogo en este momento. Intenta nuevamente en unos minutos."

    evidencia = buscar_fragmentos(pdf_text, t)

    # Si no hay evidencia → no inventar
    if not evidencia.strip():
        return "Gracias por tu consulta. No encuentro ese dato en el catálogo. ¿En qué ciudad/distrito y qué tipo de inmueble buscas?"

    if not client:
        return "El sistema de respuestas aún no está configurado (falta OPENAI_API_KEY)."

    system = (
        "Eres un asesor inmobiliario profesional. Responde únicamente usando la evidencia del catálogo. "
        "No inventes precios, ubicaciones, disponibilidad ni condiciones si no aparecen en la evidencia. "
        "Si la pregunta está fuera del catálogo, indica que solo brindas información del catálogo y pide datos para ayudar."
    )

    user = f"Pregunta del cliente: {t}\n\nEvidencia del catálogo (PDF):\n{evidencia}"

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3
    )
    return resp.choices[0].message.content.strip()


# =========================
# Enviar mensajes WhatsApp
# =========================


# =========================
# Run
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)