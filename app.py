from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import traceback
import http.client
import os
from pypdf import PdfReader
from openai import OpenAI
##from whatsapp_service import enviar_mensajes
import re
import unicodedata
from typing import List, Tuple
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

            respuesta = generar_respuesta_desde_pdf(texto)            
            enviar_mensajes(respuesta, numero, agregar_mensaje_log)

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

CODE_RE = re.compile(r"\b(?:VA|VP|VL|AR|AC)-\d{3}\b", re.IGNORECASE)


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos raros, espacios limpios."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s$/.%-]", " ", texto)  # deja $ y algunos separadores útiles
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def expandir_sinonimos(palabras: List[str]) -> List[str]:
    """
    Sinónimos típicos (chat inmobiliario). Ajusta si quieres.
    """
    mapa = {
        "depa": ["departamento", "dpto"],
        "dpto": ["departamento", "depa"],
        "depto": ["departamento"],
        "casa": ["vivienda"],
        "hab": ["dorm", "dormitorios", "habitaciones"],
        "dorm": ["dormitorios", "hab", "habitaciones"],
        "baño": ["banos", "sshh"],
        "banos": ["baño", "sshh"],
        "cochera": ["estacionamiento", "garage"],
        "garage": ["cochera", "estacionamiento"],
        "alquiler": ["renta", "arrendar", "alquilar"],
        "alquilar": ["alquiler", "renta"],
        "comprar": ["compra", "venta"],
        "venta": ["comprar", "compra"],
        "barato": ["economico", "oferta", "bajo"],
        "economico": ["barato", "oferta", "bajo"],
    }

    out = set(palabras)
    for p in list(palabras):
        for s in mapa.get(p, []):
            out.add(s)
    return list(out)


def _split_lineas(pdf_text: str) -> List[str]:
    # Conserva líneas, porque en tu PDF las tablas se extraen con saltos.
    return [ln.strip() for ln in (pdf_text or "").splitlines() if ln.strip()]


def _extraer_bloque_alrededor(lineas: List[str], idx: int, before: int = 2, after: int = 10) -> str:
    """
    Devuelve un bloque de líneas alrededor de un índice.
    Para tablas del PDF, suele ser suficiente para capturar “fila completa + encabezados”.
    """
    a = max(0, idx - before)
    b = min(len(lineas), idx + after + 1)
    return "\n".join(lineas[a:b])


def _extraer_bloque_por_codigo(lineas: List[str], codigo: str) -> str:
    """
    Si el usuario menciona un código (VA-001, etc.), devolver un bloque completo:
    desde el código hasta antes del siguiente código (o un límite).
    """
    codigo = codigo.upper()
    # encuentra la línea que contiene el código
    start = None
    for i, ln in enumerate(lineas):
        if codigo in ln.upper():
            start = i
            break
    if start is None:
        return ""

    # buscar el siguiente código para cortar “ficha”
    end = min(len(lineas), start + 25)  # límite duro para evitar bloques gigantes
    for j in range(start + 1, min(len(lineas), start + 25)):
        if CODE_RE.search(lineas[j]):
            end = j
            break

    # incluir un par de líneas antes por si hay encabezado “Inventario en Venta — Lima”
    a = max(0, start - 2)
    return "\n".join(lineas[a:end])


def buscar_fragmentos(pdf_text: str, pregunta: str, max_chars: int = 3500) -> str:
    """
    Recupera evidencia del PDF con enfoque inmobiliario:
    1) Si hay código (VA-001, etc.) → devuelve bloque por código.
    2) Si no hay código → rankea líneas por relevancia y devuelve bloques alrededor.
    """

    if not pdf_text or not pregunta:
        return ""

    lineas = _split_lineas(pdf_text)
    pregunta_norm = normalizar_texto(pregunta)

    # 1) Prioridad absoluta: si el usuario menciona código(s), devolvemos esos bloques.
    codigos = list({c.upper() for c in CODE_RE.findall(pregunta_norm)})
    if codigos:
        bloques = []
        for cod in codigos[:3]:  # limita a 3 para no explotar contexto
            b = _extraer_bloque_por_codigo(lineas, cod)
            if b:
                bloques.append(b)
        texto = "\n\n---\n\n".join(bloques)
        return texto[:max_chars] + ("\n...[contenido recortado]..." if len(texto) > max_chars else "")

    # 2) Búsqueda por relevancia (sin código)
    stopwords = {
        "que", "como", "donde", "cual", "cuanto", "cuales", "tienes", "tiene",
        "para", "con", "del", "las", "los", "una", "uno", "unos", "unas",
        "por", "sobre", "este", "esta", "estos", "estas", "a", "en", "de", "y", "o"
    }

    palabras_base = [p for p in pregunta_norm.split() if len(p) >= 3 and p not in stopwords]
    palabras = expandir_sinonimos(palabras_base)

    # señales útiles: números y dinero
    tiene_precio = bool(re.search(r"\$?\s?\d[\d,\.]*", pregunta_norm))
    nums = re.findall(r"\d+", pregunta_norm)
    nums = set(nums)

    resultados: List[Tuple[int, int]] = []  # (score, idx_linea)

    for idx, ln in enumerate(lineas):
        ln_norm = normalizar_texto(ln)

        score = 0

        # coincidencias de palabras (peso 2)
        for p in palabras:
            if p and p in ln_norm:
                score += 2

        # si la línea contiene un código de inventario, sube su peso
        if CODE_RE.search(ln):
            score += 3

        # si el usuario mencionó números (ej: 3 dormitorios, 2 baños), y la línea tiene esos números
        if nums:
            for n in nums:
                if re.search(rf"\b{re.escape(n)}\b", ln_norm):
                    score += 2

        # si el usuario mencionó precio y la línea tiene $ o “precio/mes”, sube
        if tiene_precio and ("$" in ln or "precio" in ln_norm):
            score += 2

        if score > 0:
            resultados.append((score, idx))

    # ordenar por score y tomar los mejores
    resultados.sort(key=lambda x: x[0], reverse=True)
    top = resultados[:12]  # top líneas “semilla”

    # convertir semillas a bloques (evita duplicados por solapamiento)
    bloques = []
    usados = set()
    for score, idx in top:
        # “firma” simple para no repetir el mismo bloque 10 veces
        key = max(0, idx - 2)
        if key in usados:
            continue
        usados.add(key)

        bloque = _extraer_bloque_alrededor(lineas, idx, before=2, after=10)
        bloques.append(bloque)

    texto = "\n\n---\n\n".join(bloques).strip()

    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n...[contenido recortado]..."

    return texto

def generar_respuesta_desde_pdf(texto_usuario: str) -> str:
    t = (texto_usuario or "").strip()
    if not t:
        return "¿Podrías escribir tu consulta, por favor?"

    # Saludos (sin tocar PDF ni OpenAI)
    saludos = {"hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"}
    if t.lower() in saludos:
        return "Hola, soy tu asesor(a) de Inmobiliaria Horizonte Urbano S.A.C.. ¿Deseas comprar, vender o alquilar una propiedad?"

    # Todo lo demás → catálogo
    return preguntar_catalogo(t)


# =========================
# Funcion para Preguntar OPENAI con contexto del PDF
# =========================
def preguntar_catalogo(pregunta: str) -> str:
    t = (pregunta or "").strip()
    if not t:
        return "¿Podrías escribir tu consulta, por favor?"

    if not client:
        return "El sistema aún no está configurado (falta OPENAI_API_KEY)."

    pdf_text = cargar_texto_pdf()
    if not pdf_text:
        return "No pude leer el catálogo en este momento. Intenta nuevamente en unos minutos."

    evidencia = buscar_fragmentos(pdf_text, t)

    # Si no hay evidencia → no inventar (y pedir datos)
    if not evidencia.strip():
        return ("Solo puedo brindar información del catálogo de Inmobiliaria Horizonte Urbano S.A.C. "
                "No encuentro ese dato en el catálogo. ¿En qué ciudad/distrito y qué tipo de inmueble buscas?")

    system = (
        "Eres un asesor inmobiliario profesional de 'Inmobiliaria Horizonte Urbano S.A.C'. "
        "Responde ÚNICAMENTE usando la evidencia del catálogo proporcionada. "
        "No inventes precios, ubicaciones, metrajes, disponibilidad, beneficios ni condiciones si no aparecen en la evidencia. "
        "Si el usuario pregunta algo fuera del catálogo, responde: "
        "'Solo puedo brindar información del catálogo de Inmobiliaria Horizonte Urbano S.A.C.' y pide datos (ciudad/distrito, tipo de inmueble, presupuesto)."
    )

    user = (
        f"Pregunta del cliente: {t}\n\n"
        f"Evidencia del catálogo (PDF):\n{evidencia}\n\n"
        "Responde claro, breve y comercial. Si faltan datos clave, pregunta 1-2 cosas máximo."
    )
    print("LLAMANDO A OPENAI...")
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2
    )

    return (resp.choices[0].message.content or "").strip()

# =========================
# Enviar mensajes
# =========================
# Enviar mensajes a través de la API de WhatsApp (función placeholder)    
def enviar_mensajes(texto, numero, agregar_mensaje_log):
    texto = (texto or "").strip()
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
    # Convertir el diccionario a JSON y codificar en UTF-8
    data = json.dumps(data, ensure_ascii=False).encode("utf-8")
    #Aquí iría la lógica para enviar el mensaje a través de la API de WhatsApp
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': 'Bearer EAARxR0W4Q4IBQ2AfIZAv01cd6x855ixNcE0Hb09VqZASujFeVzWGAkhs3H4cMZBE9XVrbZA51w9IyaJHOIwal6jzsJOtOl5NTuVdYF5NDrQmqd4dBJAgBiQABqEAkZBgBCt5lZAaYf8iAwlZCOe8cG3ctfKxB5eXItCTEFbChJZBTNSZCpH71fcoS9ygeYVd22ZC0ezTiJkfUPZBsz0IQCtTXV1JBjzJeHa2qzGvx8gMB1ZAjAW86tq6f3NLelEAAAnVKNr7NusKgXJNWXOX2CV7rKH5AFFZA'  # Reemplaza con tu token de acceso
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