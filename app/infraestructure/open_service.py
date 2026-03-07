# =========================
# OpenAI
# =========================
import os
from openai import OpenAI

from app.infraestructure.pdf_service import cargar_texto_pdf, buscar_fragmentos

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def preguntar_catalogo(pregunta: str) -> str:
    t = (pregunta or "").strip()
    if not t:
        return "¿Podrías escribir tu consulta, por favor?"

    if not client:
        return "El sistema aún no está configurado (falta OPENAI_API_KEY)."

    pdf_text = cargar_texto_pdf()
    if not pdf_text:
        return "No pude leer el catálogo en este momento. Intenta nuevamente en unos minutos."

    evidencia = buscar_fragmentos(pdf_text, t)

    if not evidencia.strip():
        return (
            "Solo puedo brindar información del catálogo de Inmobiliaria Horizonte Urbano S.A.C. "
            "No encuentro ese dato en el catálogo. ¿En qué ciudad/distrito y qué tipo de inmueble buscas?"
        )

    system = (
        "Eres un asesor inmobiliario profesional de 'Inmobiliaria Horizonte Urbano S.A.C'. "
        "Responde ÚNICAMENTE usando la evidencia del catálogo proporcionada. "
        "No inventes precios, ubicaciones, metrajes, disponibilidad, beneficios ni condiciones si no aparecen en la evidencia. "
        "Si el usuario pregunta algo fuera del catálogo, responde: "
        "'Solo puedo brindar información del catálogo de Inmobiliaria Horizonte Urbano S.A.C.' y pide datos "
        "(ciudad/distrito, tipo de inmueble, presupuesto)."
    )

    user = (
        f"Pregunta del cliente: {t}\n\n"
        f"Evidencia del catálogo (PDF):\n{evidencia}\n\n"
        "Responde claro, breve y comercial. Si faltan datos clave, pregunta 1-2 cosas máximo."
    )

    #print("OPENAI CALL", flush=True)
    #print("Pregunta:", t, flush=True)
    #print("Evidencia encontrada:", evidencia[:200], flush=True)

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2
    )

    return (resp.choices[0].message.content or "").strip()