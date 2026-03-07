import re
from typing import List
import unicodedata

CODE_RE = re.compile(r"\b(?:VA|VP|VL|AR|AC)-\d{3}\b", re.IGNORECASE)


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos raros, espacios limpios."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s$/.%-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def expandir_sinonimos(palabras: List[str]) -> List[str]:
    mapa = {
        "depa": ["departamento", "dpto"],
        "dpto": ["departamento", "depa"],
        "depto": ["departamento"],
        "casa": ["vivienda"],
        "hab": ["dorm", "dormitorios", "habitaciones"],
        "dorm": ["dormitorios", "hab", "habitaciones"],
        "baño": ["banos", "sshh"],
        "banos": ["baño", "sshh"],
        "cochera": ["estacionamiento", "garage"],
        "garage": ["cochera", "estacionamiento"],
        "alquiler": ["renta", "arrendar", "alquilar"],
        "alquilar": ["alquiler", "renta"],
        "comprar": ["compra", "venta"],
        "venta": ["comprar", "compra"],
        "barato": ["economico", "oferta", "bajo"],
        "economico": ["barato", "oferta", "bajo"],
    }

    out = set(palabras)
    for p in list(palabras):
        for s in mapa.get(p, []):
            out.add(s)
    return list(out)


def split_lineas(pdf_text: str) -> List[str]:
    return [ln.strip() for ln in (pdf_text or "").splitlines() if ln.strip()]


def extraer_bloque_alrededor(lineas: List[str], idx: int, before: int = 2, after: int = 10) -> str:
    a = max(0, idx - before)
    b = min(len(lineas), idx + after + 1)
    return "\n".join(lineas[a:b])


def extraer_bloque_por_codigo(lineas: List[str], codigo: str) -> str:
    codigo = codigo.upper()
    start = None

    for i, ln in enumerate(lineas):
        if codigo in ln.upper():
            start = i
            break

    if start is None:
        return ""

    end = min(len(lineas), start + 25)
    for j in range(start + 1, min(len(lineas), start + 25)):
        if CODE_RE.search(lineas[j]):
            end = j
            break

    a = max(0, start - 2)
    return "\n".join(lineas[a:end])