from flask import Flask, json, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
#Modelo de la tabla log de mensajes
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fech_y_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    texto = db.Column(db.Text, nullable=False) 
#Crear la tabla si no existe
with app.app_context():
    db.create_all()

#Funcion para ordenar los registros de la tabla log por fecha y hora de forma descendente
def obtener_logs_ordenados():
    logs_ordenados = Log.query.order_by(Log.fech_y_hora.desc()).all()
    return logs_ordenados
@app.route('/')
#obtener todos los registros de la tabla log
def index():
    logs = obtener_logs_ordenados()
    return render_template('index.html', logs=logs)

mensajes_log = []
#Función para agregar un nuevo mensaje y agregarlo a la base de datos y a la lista de mensajes_log
def agregar_mensaje_log(texto):
    mensajes_log.append(texto)
    #Guardar el mensaje en la base de datos
    nuevo_log = Log(texto=texto)
    db.session.add(nuevo_log)
    db.session.commit()

#TOKEN DE VERIFICACION DE WHATBOT, REEMPLAZA 'tu_token_aqui' CON EL TOKEN REAL    
TOKEN_WHATBOT = 'tu_token_aqui'
@app.route('/webhook', methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        challenge = verificar_token(request)
        return challenge, 200
    elif request.method == 'POST':
        response=recibir_mensaje(request)
        return response, 200
def verificar_token(request):
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if token == TOKEN_WHATBOT:
        return challenge
    else:
        return jsonify({'error': 'Token de verificación no válido'}), 403
def recibir_mensaje(request):
    request =request.get_json()
    agregar_mensaje_log(request)
    return jsonify({'message': 'EVENT_RECEIVED'}) 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)