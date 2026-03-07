# =========================
# Funcion para respuesta del PDF
# =========================
from app.infraestructure.open_service import preguntar_catalogo


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
