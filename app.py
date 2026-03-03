from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import traceback
import http.client
import os
from openai import OpenAI

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


def obtener_logs_ordenados():
    return Log.query.order_by(Log.fech_y_hora.desc()).all()


@app.route('/')
def index():
    logs = obtener_logs_ordenados()
    return render_template('index.html', logs=logs)


def agregar_mensaje_log(texto):
    if not isinstance(texto, str):
        texto = json.dumps(texto, ensure_ascii=False)

    nuevo_log = Log(texto=texto)
    db.session.add(nuevo_log)
    db.session.commit()


# =========================
# Webhook WhatsApp (Meta)
# =========================
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

        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        mensaje = value.get("messages", [])

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

            respuesta = generar_respuesta_desde_txt(texto)
            enviar_mensajes(respuesta, numero)

        return jsonify({'message': 'EVENT_RECEIVED'}), 200

    except Exception as e:
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log(detalle)
        return jsonify({'error': 'Internal Server Error'}), 500


# =========================
# OpenAI + TXT
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TXT_PATH = os.environ.get("TXT_PATH", "Docs/catalogo.txt")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
_txt_text_cache = None


def cargar_texto_txt():
    global _txt_text_cache
    if _txt_text_cache is not None:
        return _txt_text_cache

    if not os.path.exists(TXT_PATH):
        agregar_mensaje_log(f"ERROR: No existe el TXT en la ruta: {TXT_PATH}")
        _txt_text_cache = ""
        return _txt_text_cache

    with open(TXT_PATH, "r", encoding="utf-8") as f:
        _txt_text_cache = f.read()

    return _txt_text_cache


def buscar_fragmentos_txt(txt_text: str, pregunta: str, max_chars: int = 4500):
    """
    Búsqueda simple pero más efectiva para TXT:
    - Parte por bloques (páginas) usando '===== PÁGINA'
    - Si encuentra keywords en un bloque, devuelve el bloque completo
    """
    q = (pregunta or "").lower()
    palabras = [p for p in q.replace("¿", " ").replace("?", " ").split() if len(p) >= 3]

    bloques = txt_text.split("===== PÁGINA")
    encontrados = []

    for i, b in enumerate(bloques):
        bloque = b.strip()
        if not bloque:
            continue

        bl = bloque.lower()
        if any(p in bl for p in palabras):
            encontrados.append("===== PÁGINA" + bloque)

    texto = "\n\n".join(encontrados).strip()
    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n...[recortado]..."
    return texto


def generar_respuesta_desde_txt(texto_usuario: str) -> str:
    t = (texto_usuario or "").strip()

    if t.lower() in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"]:
        return "Hola, bienvenido(a) a nuestra inmobiliaria. ¿Deseas comprar, vender o alquilar una propiedad?"

    txt_text = cargar_texto_txt()
    if not txt_text:
        return "No pude leer el catálogo en este momento. Intenta nuevamente en unos minutos."

    evidencia = buscar_fragmentos_txt(txt_text, t)

    if not evidencia.strip():
        return "Gracias por tu consulta. No encuentro ese dato en el catálogo. ¿En qué ciudad/distrito y qué tipo de inmueble buscas?"

    if not client:
        return "El sistema de respuestas aún no está configurado (falta OPENAI_API_KEY)."

    system = (
        "Eres un asesor inmobiliario profesional. Responde únicamente usando la evidencia del catálogo. "
        "No inventes precios, ubicaciones, disponibilidad ni condiciones si no aparecen en la evidencia. "
        "Si la pregunta está fuera del catálogo, indica que solo brindas información del catálogo y pide datos para ayudar."
    )

    user = f"Pregunta del cliente: {t}\n\nEvidencia del catálogo (TXT):\n{evidencia}"

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
def enviar_mensajes(texto, numero):
    texto = texto.lower()
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": texto
        }
    }

    data = json.dumps(data, ensure_ascii=False).encode("utf-8")

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': 'Bearer EAARxR0W4Q4IBQ4X0S8DfieZCQd2ftnZB4jZAo8cU2pfScGeccjZBEwQ072YfqNfyN9SYKTZB78snbHxpDSZCVQ6qk8rZATBG9ZBhIZCekFZC6CFdzVLPHPvpQfbiCsZAX8nYYYV19HhlhRiMgi7gME0JcIuEAzcZBww84PNA1tnFDkxgJVwltMZBlnvO0DNvzaBB5mC4kZB2d9n6AjvqQ50P8DQnzYqNvZCiZAMfdiDrlAOMQZAcNMo47ZBdk5fZAtgeR7NAcvRaTaVOIrNDiDaTJZCkokcKztj8jW5P'
    }

    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', '/v22.0/1009924102202593/messages', body=data, headers=headers)
        response = connection.getresponse()
        print(response.status, response.reason)
        print(response.read().decode())
    except Exception as e:
        agregar_mensaje_log(json.dumps({
            "error": "Error al enviar mensaje",
            "detalle": str(e)
        }, ensure_ascii=False))
    finally:
        connection.close()


# =========================
# Run
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)