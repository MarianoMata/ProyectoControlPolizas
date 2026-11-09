"""Servicio para generar avisos de renovación de póliza en PDF.

Usa fpdf2 para crear un documento A4 vertical y lo devuelve en bytes.
"""

from datetime import date

from fpdf import FPDF

from models.polizas import FECHA_CORTE, estado_poliza

COLOR_ROJO = (174, 24, 0)      # #AE1800
COLOR_GRIS = (240, 240, 240)   # fondo del pie de página
COLOR_TEXTO_GRIS = (100, 100, 100)


def _latin1(texto):
    """Convierte texto a latin-1 para que las tildes no fallen en Helvetica."""
    if texto is None:
        return ""
    return str(texto).encode("latin-1", errors="replace").decode("latin-1")


def _fmt_fecha(d):
    """Formatea un objeto date como dd/mm/aaaa o devuelve 'No registrada'."""
    if d is None:
        return "No registrada"
    return d.strftime("%d/%m/%Y")


def _fmt_monto(valor):
    """Formatea un monto como 'CRC 228,000.00' o 'No registrada' si es None."""
    if valor is None:
        return "No registrada"
    return f"CRC {valor:,.2f}"


def crear_aviso_pdf(poliza):
    """Crea un aviso de renovación en PDF (A4 vertical) y lo devuelve en bytes.

    El diccionario poliza debe contener al menos:
        nombre, numero, aseguradora, ramo, cedula, desde, hasta, prima, pago, asesor
    y opcionalmente estado y dias_hasta (si no vienen, se calculan).
    """
    # Calcular estado y días si no vienen en el diccionario
    hasta = poliza.get("hasta")
    estado = poliza.get("estado") or estado_poliza(hasta, FECHA_CORTE)
    if poliza.get("dias_hasta") is None and hasta is not None:
        dias_hasta = (hasta - FECHA_CORTE).days
    else:
        dias_hasta = poliza.get("dias_hasta")

    pdf = FPDF(format="A4", unit="mm")
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # ---------- Banda superior roja ----------
    pdf.set_fill_color(*COLOR_ROJO)
    pdf.set_text_color(255, 255, 255)

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 16, _latin1("Corredora de Seguros Horizonte"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, _latin1("Aviso de renovación de póliza"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    pdf.ln(6)

    # ---------- Cuerpo ----------
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(0, 0, 0)

    # Saludo
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, _latin1(f"Estimado(a) {poliza.get('nombre', '')}"),
             new_x="LMARGIN", new_y="NEXT")

    # Párrafo según estado
    if estado == "Vencida":
        parrafo = f"Su póliza venció el {_fmt_fecha(hasta)}."
    elif estado == "Por vencer":
        asesor = poliza.get("asesor", "")
        parrafo = (f"Su póliza vence el {_fmt_fecha(hasta)} en {dias_hasta} días. "
                   f"Su asesor {asesor} se comunicará con usted.")
    else:
        parrafo = "Su póliza se encuentra vigente."

    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 7, _latin1(parrafo))
    pdf.ln(5)

    # ---------- Tabla ----------
    pdf.set_font("helvetica", "B", 10)
    columnas = ["Número de póliza", "Aseguradora", "Ramo", "Cédula",
                "Vigencia", "Prima anual", "Forma de pago"]
    anchos = [30, 45, 25, 25, 40, 30, 30]

    for col, ancho in zip(columnas, anchos):
        pdf.cell(ancho, 8, _latin1(col), border=1, align="C")
    pdf.ln()

    pdf.set_font("helvetica", "", 10)
    desde = poliza.get("desde")
    vigencia = f"{_fmt_fecha(desde)} al {_fmt_fecha(hasta)}"

    valores = [
        poliza.get("numero", ""),
        poliza.get("aseguradora", ""),
        poliza.get("ramo", ""),
        poliza.get("cedula", ""),
        vigencia,
        _fmt_monto(poliza.get("prima")),
        poliza.get("pago", ""),
    ]

    for val, ancho in zip(valores, anchos):
        pdf.cell(ancho, 8, _latin1(val), border=1)
    pdf.ln(10)

    # ---------- Pie de página gris ----------
    pdf.set_fill_color(*COLOR_GRIS)
    pdf.set_text_color(*COLOR_TEXTO_GRIS)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 8, _latin1("Documento ficticio con fines académicos."),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    # Devolver bytes
    return bytes(pdf.output(dest="S"))
