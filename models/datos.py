"""Acceso a datos de la bodega data/.

Es el único lugar que abre archivos de entrada:
- Maestro_Clientes.xlsx (hoja Clientes)
- PDFs de pólizas en data/polizas/
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import pdfplumber

DATA_DIR = Path("data")
CLIENTES_XLSX = DATA_DIR / "Maestro_Clientes.xlsx"
POLIZAS_DIR = DATA_DIR / "polizas"

# Diccionario: etiqueta del PDF -> nombre del campo interno
CAMPOS = {
    "Numero de poliza": "numero",
    "Ramo": "ramo",
    "Tomador / Asegurado": "nombre",
    "Cedula": "cedula",
    "Vigencia desde": "desde",
    "Vigencia hasta": "hasta",
    "Prima anual": "prima",
    "Forma de pago": "pago",
    "Suma asegurada": "suma",
    "Asesor": "asesor",
}


def _texto_a_fecha(texto):
    """Convierte 'dd/mm/aaaa' a objeto date. Devuelve None si está vacío o es inválido."""
    if not texto or not texto.strip():
        return None
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _texto_a_numero(texto):
    """Convierte 'CRC 228,000.00' a float. Devuelve None si está vacío."""
    if not texto or not texto.strip():
        return None
    limpio = texto.strip().replace("CRC", "").replace(",", "").strip()
    if not limpio:
        return None
    try:
        return float(limpio)
    except ValueError:
        return None


def cargar_clientes():
    """Lee Maestro_Clientes.xlsx (hoja Clientes) y devuelve DataFrame con Cedula como texto sin espacios."""
    df = pd.read_excel(CLIENTES_XLSX, sheet_name="Clientes")
    df["Cedula"] = df["Cedula"].astype(str).str.strip()
    return df


def leer_poliza(ruta_pdf):
    """Extrae datos de un PDF de póliza y devuelve un diccionario.

    Estructura del diccionario devuelto:
        archivo, aseguradora, numero, ramo, nombre, cedula,
        desde, hasta, prima, pago, suma, asesor
    """
    ruta = Path(ruta_pdf)

    with pdfplumber.open(ruta) as pdf:
        pagina = pdf.pages[0]
        texto = pagina.extract_text() or ""

    lineas = texto.split("\n")
    if not lineas:
        return {
            "archivo": ruta.name,
            "aseguradora": "",
            "numero": "",
            "ramo": "",
            "nombre": "",
            "cedula": "",
            "desde": None,
            "hasta": None,
            "prima": None,
            "pago": "",
            "suma": None,
            "asesor": "",
        }

    # La primera línea es el nombre de la aseguradora
    aseguradora = lineas[0].strip()

    resultado = {
        "archivo": ruta.name,
        "aseguradora": aseguradora,
        "numero": "",
        "ramo": "",
        "nombre": "",
        "cedula": "",
        "desde": None,
        "hasta": None,
        "prima": None,
        "pago": "",
        "suma": None,
        "asesor": "",
    }

    # Recorrer las demás líneas con un bucle
    for linea in lineas[1:]:
        if ":" in linea:
            etiqueta, valor = linea.split(":", 1)
            etiqueta = etiqueta.strip()
            valor = valor.strip()
            if etiqueta in CAMPOS:
                campo = CAMPOS[etiqueta]
                if campo in ("desde", "hasta"):
                    resultado[campo] = _texto_a_fecha(valor)
                elif campo in ("prima", "suma"):
                    resultado[campo] = _texto_a_numero(valor)
                else:
                    resultado[campo] = valor

    return resultado


def cargar_polizas():
    """Recorre data/polizas en orden alfabético y devuelve una lista con el diccionario de cada PDF."""
    polizas = []
    if not POLIZAS_DIR.exists():
        return polizas
    for archivo in sorted(POLIZAS_DIR.iterdir()):
        if archivo.suffix.lower() == ".pdf":
            polizas.append(leer_poliza(archivo))
    return polizas
