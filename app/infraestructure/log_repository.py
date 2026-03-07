import json
from app.infraestructure.database import db
from app.domain.models import Log

def obtener_logs_ordenados():
    return Log.query.order_by(Log.fech_y_hora.desc()).all()

def agregar_mensaje_log(data):
    """
    Acepta dict o string JSON.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {
                "numero": None,
                "tipo": "sistema",
                "texto": data
            }

    nuevo_log = Log(
        numero=data.get("numero"),
        tipo=data.get("tipo"),
        texto=data.get("texto") or data.get("error") or str(data)
    )

    db.session.add(nuevo_log)
    db.session.commit()