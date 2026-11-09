"""Controlador de pólizas — rutas de Flask.

No calcula nada: solo llama a models/ y services/.
"""

import io
import zipfile

from flask import Blueprint, render_template, send_file, abort, request

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
