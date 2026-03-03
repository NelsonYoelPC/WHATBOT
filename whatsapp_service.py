import json
import http.client


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
        'Authorization': 'Bearer EAARxR0W4Q4IBQ4X0S8DfieZCQd2ftnZB4jZAo8cU2pfScGeccjZBEwQ072YfqNfyN9SYKTZB78snbHxpDSZCVQ6qk8rZATBG9ZBhIZCekFZC6CFdzVLPHPvpQfbiCsZAX8nYYYV19HhlhRiMgi7gME0JcIuEAzcZBww84PNA1tnFDkxgJVwltMZBlnvO0DNvzaBB5mC4kZB2d9n6AjvqQ50P8DQnzYqNvZCiZAMfdiDrlAOMQZAcNMo47ZBdk5fZAtgeR7NAcvRaTaVOIrNDiDaTJZCkokcKztj8jW5P'
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