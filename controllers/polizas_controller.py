"""Controlador de pólizas — rutas de Flask.

No calcula nada: solo llama a models/ y services/.
"""

import csv
import io
import os
import zipfile
from tempfile import gettempdir

from flask import (
    Blueprint,
    render_template,
    send_file,
    abort,
    request,
    session,
    redirect,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename

from models.datos import cargar_clientes
from models.polizas import (
    calcular_resultados,
    contar_por_estado,
    primas_por_aseguradora,
    buscar_inconsistencias,
    buscar_por_numero,
    FECHA_CORTE,
)
from services.generador_aviso import crear_aviso_pdf

bp = Blueprint("polizas", __name__)

# Extensiones permitidas para subir Excel
EXTENSIONES_PERMITIDAS = {".xlsx", ".xls"}


def _excel_es_valido(nombre_archivo):
    """Devuelve True si el nombre termina en .xlsx o .xls."""
    _, extension = os.path.splitext(nombre_archivo)
    return extension.lower() in EXTENSIONES_PERMITIDAS


def _ruta_excel_actual():
    """Devuelve la ruta del Excel de clientes guardado en la sesión,
    o None si no hay uno subido."""
    return session.get("ruta_excel_clientes")


@bp.route("/")
def inicio():
    """Tablero principal: muestra la vista inicio.html con todos los datos."""
    ruta_excel = _ruta_excel_actual()
    if ruta_excel and os.path.exists(ruta_excel):
        clientes = cargar_clientes(ruta_excel)
        usando_excel_subido = True
    else:
        clientes = None  # calcular_resultados usará el maestro de data/
        usando_excel_subido = False

    resultados = calcular_resultados(clientes)
    conteo = contar_por_estado(resultados)
    primas = primas_por_aseguradora(resultados)
    inconsistencias = buscar_inconsistencias(resultados)

    return render_template(
        "inicio.html",
        resultados=resultados,
        conteo=conteo,
        primas=primas,
        inconsistencias=inconsistencias,
        fecha_corte=FECHA_CORTE,
        usando_excel_subido=usando_excel_subido,
    )


@bp.route("/subir-excel", methods=["POST"])
def subir_excel():
    """Recibe un Excel de clientes, lo guarda temporalmente y lo registra en la sesión."""
    if "archivo_excel" not in request.files:
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for("polizas.inicio"))

    archivo = request.files["archivo_excel"]
    if archivo.filename == "":
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for("polizas.inicio"))

    if not _excel_es_valido(archivo.filename):
        flash("El archivo debe ser un Excel (.xlsx o .xls).", "error")
        return redirect(url_for("polizas.inicio"))

    # Guardar el archivo subido en la carpeta temporal del sistema
    nombre_seguro = secure_filename(archivo.filename)
    ruta_guardado = os.path.join(gettempdir(), nombre_seguro)
    archivo.save(ruta_guardado)

    # Recordar la ruta en la sesión para usarla en los cálculos
    session["ruta_excel_clientes"] = ruta_guardado
    flash(f"Excel cargado: {archivo.filename}", "exito")
    return redirect(url_for("polizas.inicio"))


@bp.route("/ejecutar")
def ejecutar():
    """Recalcula los resultados con el Excel actual (subido o el maestro por defecto)."""
    # Forzamos recarga: calcular_resultados ya lee de la sesión vía _ruta_excel_actual
    # dentro de inicio, pero aquí solo redirigimos al tablero con datos frescos.
    flash("Resultados recalculados.", "exito")
    return redirect(url_for("polizas.inicio"))


@bp.route("/exportar-notificaciones")
def exportar_notificaciones():
    """Descarga un CSV con las pólizas Por vencer y Vencidas (las que necesitan aviso)."""
    ruta_excel = _ruta_excel_actual()
    if ruta_excel and os.path.exists(ruta_excel):
        clientes = cargar_clientes(ruta_excel)
    else:
        clientes = None

    resultados = calcular_resultados(clientes)

    # Filtrar solo las que necesitan notificación
    notificaciones = [
        r for r in resultados if r["estado"] in ("Por vencer", "Vencida")
    ]

    # Crear CSV en memoria
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(
        [
            "Numero de poliza",
            "Asegurado",
            "Cedula",
            "Aseguradora",
            "Ramo",
            "Vigencia hasta",
            "Dias hasta vencer",
            "Prima anual",
            "Estado",
        ]
    )
    for r in notificaciones:
        hasta = r["hasta"].strftime("%d/%m/%Y") if r["hasta"] else ""
        prima = f"{r['prima']:.2f}" if r["prima"] is not None else ""
        escritor.writerow(
            [
                r["numero"],
                r["nombre"],
                r["cedula"],
                r["aseguradora"],
                r["ramo"],
                hasta,
                r["dias_hasta"] if r["dias_hasta"] is not None else "",
                prima,
                r["estado"],
            ]
        )

    csv_bytes = buffer.getvalue().encode("utf-8")
    buffer.close()

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name="notificaciones_polizas.csv",
    )


@bp.route("/")
def inicio():
    """Tablero principal: muestra la vista inicio.html con todos los datos."""
    resultados = calcular_resultados()
    conteo = contar_por_estado(resultados)
    primas = primas_por_aseguradora(resultados)
    inconsistencias = buscar_inconsistencias(resultados)

    return render_template(
        "inicio.html",
        resultados=resultados,
        conteo=conteo,
        primas=primas,
        inconsistencias=inconsistencias,
        fecha_corte=FECHA_CORTE,
    )


@bp.route("/aviso/")
def aviso():
    """Devuelve el PDF de aviso de una póliza específica.

    Se espera el número de póliza como parámetro de query: /aviso/?numero=AIS-2026-0001
    Si no existe o está Vigente, devuelve error 404.
    """
    numero = request.args.get("numero")
    if not numero:
        abort(404)

    resultados = calcular_resultados()
    poliza = buscar_por_numero(numero, resultados)

    if poliza is None or poliza["estado"] == "Vigente":
        abort(404)

    pdf_bytes = crear_aviso_pdf(poliza)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"aviso_{numero}.pdf",
    )


@bp.route("/descargar-avisos")
def descargar_avisos():
    """Crea en memoria un .zip con los avisos de pólizas Por vencer y Vencidas."""
    resultados = calcular_resultados()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in resultados:
            if r["estado"] in ("Por vencer", "Vencida"):
                pdf_bytes = crear_aviso_pdf(r)
                zf.writestr(f"aviso_{r['numero']}.pdf", pdf_bytes)

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="avisos.zip",
    )
