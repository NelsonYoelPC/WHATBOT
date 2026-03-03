from flask import Flask, json, render_template
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
    prueba1 = Log(texto="Mensaje de prueba1")
    prueba2 = Log(texto="Mensaje de prueba2")
    db.session.add(prueba1)
    db.session.add(prueba2)
    db.session.commit()
#Funcion para ordenar los registros de la tabla log por fecha y hora de forma descendente
def obtener_logs_ordenados():
    logs_ordenados = Log.query.order_by(Log.fech_y_hora.desc()).all()
    return logs_ordenados
@app.route('/')
def index():
    #obtener todos los registros de la tabla log
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
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)