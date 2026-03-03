from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import traceback
import http.client
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de la tabla log de mensajes (errores)
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

        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # A veces Meta manda eventos sin "messages" (por ejemplo statuses)
        mensaje = value.get("messages", [])

        #Si NO hay mensajes, no guardamos nada (no es error)
        if not mensaje:
            return jsonify({'message': 'EVENT_RECEIVED'}), 200

        messages = mensaje[0]

        # Validación de tipo
        tipo = messages.get("type")

        if tipo == "interactive":
            # si no quieres guardar interactivos, solo confirma recepción
            return jsonify({'message': 'EVENT_RECEIVED'}), 200

        if tipo == "text":
            texto = (messages.get("text") or {}).get("body", "")
            numero = messages.get("from", "")

            enviar_mensajes(texto, numero)

        return jsonify({'message': 'EVENT_RECEIVED'}), 200

    except Exception as e:
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log(detalle)
        return jsonify({'error': 'Internal Server Error'}), 500
#Enviar mensajes a través de la API de WhatsApp (función placeholder)    
def enviar_mensajes(texto, numero):
    texto=texto.lower()
    if "hola" in texto:
        data={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero    ,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Hola, ¿en qué puedo ayudarte?"
            }
        }
    else:
        data={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero    ,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Intente nuevamente, no entendí su mensaje."
            }
        }
    #Convertir el diccionario a JSON 
    data= json.dumps(data, ensure_ascii=False)
    #Aquí iría la lógica para enviar el mensaje a través de la API de WhatsApp
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAARxR0W4Q4IBQ2dDSXDdU0Ts57jmQeKAylRvZA0hXzUdRZBYo3A6D836NGwVbVU7ZBZAvADDPJGpRycGRZCjeKEKV3Jst6HPOxU8nP9OYqkPBEnoMQ4SLBsZA5Lx55K1ZCUHhZAKKkZBxZAUWcEc66qFdiwkJs5faWE6oSiPWuAowZA9coqxu893PqZAUrwFfZC65bPjJ44ZBZAXG2TZBtDXy8wGYNMjZAZAO5YGY1FlEZA00G6LPVtBZCS1aMMWgES1uZARuu4UIHMRhjuDsMbmuf2Xcd3y9UehZAw0yZAPgZDZD'  # Reemplaza con tu token de acceso
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
    
if __name__ == '__main__':
    # Para Render luego cámbialo a PORT dinámico, pero lo dejo igual a tu estilo actual:
    app.run(host='0.0.0.0', port=80, debug=True)