# =========================
# Funcion para recibir mensajes de WhatsApp (Meta)
# =========================
from app.application.generar_respuesta import generar_respuesta_desde_pdf
from app.infraestructure.log_repository import agregar_mensaje_log
from app.infraestructure.whatsapp_service import enviar_mensajes

def procesar_mensaje_texto(numero: str, texto: str):
    agregar_mensaje_log({
        "numero": numero,
        "tipo": "usuario",
        "texto": texto
    })

    respuesta = generar_respuesta_desde_pdf(texto)

    agregar_mensaje_log({
        "numero": numero,
        "tipo": "bot",
        "texto": respuesta
    })

    enviar_mensajes(respuesta, numero)