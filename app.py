from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import traceback

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
    return jsonify({'error': 'Token de verificación no válido'}), 403

def recibir_mensaje(req):
    try:
        data = req.get_json(silent=True)
        if data is None:
            # JSON vacío o inválido: registrar como error
            agregar_mensaje_log("Error: Body no es JSON válido o está vacío.")
            return jsonify({'error': 'Invalid JSON'}), 400

        # ✅ Aquí NO guardamos nada si todo salió bien (solo errores)
        return jsonify({'message': 'EVENT_RECEIVED'}), 200

    except Exception as e:
        # Registrar SOLO el error real con traceback
        detalle = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        agregar_mensaje_log(detalle)
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    # Para Render luego cámbialo a PORT dinámico, pero lo dejo igual a tu estilo actual:
    app.run(host='0.0.0.0', port=80, debug=True)