import os
import re
from typing import List, Tuple
from pypdf import PdfReader

from app.infraestructure.log_repository import agregar_mensaje_log
from app.utils.text_utils import (
    CODE_RE,
    normalizar_texto,
    expandir_sinonimos,
    split_lineas,
    extraer_bloque_alrededor,
    extraer_bloque_por_codigo,
)
PDF_PATH = os.environ.get("PDF_PATH", "Docs/catalogo.pdf")
_pdf_text_cache = None

def cargar_texto_pdf():
    global _pdf_text_cache

    if _pdf_text_cache is not None:
        return _pdf_text_cache

    if not os.path.exists(PDF_PATH):
        agregar_mensaje_log(f"ERROR: No existe el PDF en la ruta: {PDF_PATH}")
        _pdf_text_cache = ""
        return _pdf_text_cache

    reader = PdfReader(PDF_PATH)
    parts = []

    for i, page in enumerate(reader.pages):
        t = (page.extract_text() or "").strip()
        if t:
            parts.append(f"[Página {i+1}]\n{t}")

    _pdf_text_cache = "\n\n".join(parts)
    return _pdf_text_cache

def buscar_fragmentos(pdf_text: str, pregunta: str, max_chars: int = 3500) -> str:
    if not pdf_text or not pregunta:
        return ""

    lineas = split_lineas(pdf_text)
    pregunta_norm = normalizar_texto(pregunta)

    codigos = list({c.upper() for c in CODE_RE.findall(pregunta_norm)})
    if codigos:
        bloques = []
        for cod in codigos[:3]:
            b = extraer_bloque_por_codigo(lineas, cod)
            if b:
                bloques.append(b)

        texto = "\n\n---\n\n".join(bloques)
        return texto[:max_chars] + ("\n...[contenido recortado]..." if len(texto) > max_chars else "")

    stopwords = {
        "que", "como", "donde", "cual", "cuanto", "cuales", "tienes", "tiene",
        "para", "con", "del", "las", "los", "una", "uno", "unos", "unas",
        "por", "sobre", "este", "esta", "estos", "estas", "a", "en", "de", "y", "o"
    }

    palabras_base = [p for p in pregunta_norm.split() if len(p) >= 3 and p not in stopwords]
    palabras = expandir_sinonimos(palabras_base)

    tiene_precio = bool(re.search(r"\$?\s?\d[\d,\.]*", pregunta_norm))
    nums = set(re.findall(r"\d+", pregunta_norm))

    resultados: List[Tuple[int, int]] = []

    for idx, ln in enumerate(lineas):
        ln_norm = normalizar_texto(ln)
        score = 0

        for p in palabras:
            if p and p in ln_norm:
                score += 2

        if CODE_RE.search(ln):
            score += 3

        if nums:
            for n in nums:
                if re.search(rf"\b{re.escape(n)}\b", ln_norm):
                    score += 2

        if tiene_precio and ("$" in ln or "precio" in ln_norm):
            score += 2

        if score > 0:
            resultados.append((score, idx))

    resultados.sort(key=lambda x: x[0], reverse=True)
    top = resultados[:12]

    bloques = []
    usados = set()

    for score, idx in top:
        key = max(0, idx - 2)
        if key in usados:
            continue

        usados.add(key)
        bloque = extraer_bloque_alrededor(lineas, idx, before=2, after=10)
        bloques.append(bloque)

    texto = "\n\n---\n\n".join(bloques).strip()

    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n...[contenido recortado]..."

    return texto