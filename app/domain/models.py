from datetime import datetime
from app.infraestructure.database import db

class Log(db.Model):
    __tablename__ = "log"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20))
    tipo = db.Column(db.String(20))
    texto = db.Column(db.Text, nullable=False)
    fech_y_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)