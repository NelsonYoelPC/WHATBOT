import json
import http.client
import os
from app.infraestructure.log_repository import agregar_mensaje_log

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
def enviar_mensajes(texto, numero, agregar_mensaje_log):
    texto = texto.strip().lower()
    if "hola" in texto:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Hola, ¿en qué puedo ayudarte? Puedes escribir compra, alquiler o venta."
            }
        }

    elif "compr" in texto:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Perfecto, te ayudo con la compra. Indícame ciudad, tipo de inmueble y presupuesto máximo."
            }
        }

    elif "alquil" in texto:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Perfecto, te ayudo con el alquiler. Dime ciudad, tipo de inmueble y presupuesto mensual."
            }
        }

    elif "vend" in texto:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Perfecto, te ayudo a vender tu propiedad. Indícame ciudad, tipo de inmueble y precio esperado."
            }
        }

    else:
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": "Puedo ayudarte con compra, alquiler o venta. ¿Cuál te interesa?"
            }
        }
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': 'Bearer EAARxR0W4Q4IBQZBZBxL8ZCb2G4JTOdYT07nL4tf9LpSqVtAtuOUfXQZAABNxVqJ3t9CGJ8NwUtZAANpZBTGgLCKNZB1ItV1sbBzx8rSpWBq7AVvZCcxa1kAupA0FrYKuHS0rKwbvxDScxkM1x83Qyzbnx0NgwMTchhBqLdUhLDh362q7qiyVrzkxGhfsLnoFEJBZBkDa4VGTFDs357RVciLZBa864ARiXYrmCqBd5WxgJnIKpomzr92fZA5XDG6Kvui6Qahp2BpjwRZCGtLbQnUej0Ru7ZA8ouQZDZD'
    }

    connection = http.client.HTTPSConnection('graph.facebook.com')

    try:
        connection.request(
            'POST',
            '/v22.0/1009924102202593/messages',
            body=body,
            headers=headers
        )

        response = connection.getresponse()
        resp_body = response.read().decode()

        # Guardamos en log para depuración
        agregar_mensaje_log({
            "whatsapp_status": response.status,
            "whatsapp_reason": response.reason,
            "whatsapp_body": resp_body
        })

    except Exception as e:
        agregar_mensaje_log({
            "error": "Error enviando mensaje",
            "detalle": str(e)
        })

    finally:
        connection.close()