"""Reglas del negocio para pólizas de seguros.

Este módulo contiene las constantes y funciones para clasificar pólizas,
contar por estado, sumar primas, buscar inconsistencias y buscar por número.
No abre archivos directamente: usa models/datos.py para leer la bodega data/.
"""

from datetime import date
from collections import defaultdict

from models.datos import cargar_clientes, cargar_polizas

FECHA_CORTE = date(2026, 11, 9)
DIAS_AVISO = 30


def estado_poliza(hasta, fecha_corte=FECHA_CORTE):
    """Devuelve el estado de una póliza: 'Vencida', 'Por vencer', 'Vigente' o 'Sin fecha'.

    Reglas:
    - Sin fecha: si hasta es None
    - Vencida: hasta < fecha_corte
    - Por vencer: 0 <= dias hasta vencer <= DIAS_AVISO
    - Vigente: más de DIAS_AVISO días
    """
    if hasta is None:
        return "Sin fecha"
    dias = (hasta - fecha_corte).days
    if hasta < fecha_corte:
        return "Vencida"
    elif 0 <= dias <= DIAS_AVISO:
        return "Por vencer"
    else:
        return "Vigente"


def calcular_resultados(fecha_corte=FECHA_CORTE):
    """Cruza cada póliza con el maestro por cédula, calcula días hasta vencer y estado.

    Devuelve una lista de diccionarios ordenada de menos a más días
    (lo urgente primero).
    """
    clientes = cargar_clientes()
    polizas = cargar_polizas()

    # Diccionario rápido: cedula -> info del cliente (correo, nombre)
    clientes_por_cedula = {}
    for _, fila in clientes.iterrows():
        cedula = str(fila["Cedula"]).strip()
        clientes_por_cedula[cedula] = {
            "correo": fila.get("Correo", ""),
            "nombre": fila.get("Nombre_Completo", ""),
        }

    resultados = []
    for p in polizas:
        cedula = str(p.get("cedula", "")).strip()
        info = clientes_por_cedula.get(cedula, {"correo": "", "nombre": ""})
        en_maestro = cedula in clientes_por_cedula

        desde = p.get("desde")
        hasta = p.get("hasta")

        if hasta is not None:
            dias_hasta = (hasta - fecha_corte).days
        else:
            dias_hasta = None

        estado = estado_poliza(hasta, fecha_corte)

        resultado = {
            "archivo": p.get("archivo", ""),
            "aseguradora": p.get("aseguradora", ""),
            "numero": p.get("numero", ""),
            "ramo": p.get("ramo", ""),
            "nombre": p.get("nombre", ""),
            "cedula": cedula,
            "correo": info["correo"],
            "en_maestro": en_maestro,
            "desde": desde,
            "hasta": hasta,
            "dias_hasta": dias_hasta,
            "prima": p.get("prima"),
            "pago": p.get("pago", ""),
            "suma": p.get("suma"),
            "asesor": p.get("asesor", ""),
            "estado": estado,
        }
        resultados.append(resultado)

    # Ordenar de menos a más días (lo urgente primero)
    def clave_orden(r):
        d = r["dias_hasta"]
        if d is None:
            return float("inf")
        return d

    resultados.sort(key=clave_orden)
    return resultados


def contar_por_estado(resultados):
    """Devuelve un diccionario con cuántas pólizas hay de cada estado."""
    conteo = {}
    for r in resultados:
        estado = r["estado"]
        conteo[estado] = conteo.get(estado, 0) + 1
    return conteo


def primas_por_aseguradora(resultados):
    """Devuelve un diccionario aseguradora -> suma de primas no vencidas,
    ordenado de mayor a menor."""
    sumas = defaultdict(float)
    for r in resultados:
        if r["estado"] != "Vencida" and r.get("prima") is not None:
            sumas[r["aseguradora"]] += r["prima"]
    ordenado = dict(sorted(sumas.items(), key=lambda item: item[1], reverse=True))
    return ordenado


def buscar_inconsistencias(resultados):
    """Devuelve una lista de textos con los 3 tipos de problema definidos en AGENTS.md.

    1. Cliente del maestro sin ninguna póliza.
    2. Póliza cuya cédula no está en el maestro.
    3. Póliza sin prima o con fecha ilegible.
    """
    inconsistencias = []
    clientes = cargar_clientes()

    # Conjunto de cédulas del maestro
    cedulas_maestro = set()
    for _, fila in clientes.iterrows():
        cedulas_maestro.add(str(fila["Cedula"]).strip())

    # Conjunto de cédulas que aparecen en pólizas
    cedulas_en_polizas = set()
    for r in resultados:
        if r["cedula"]:
            cedulas_en_polizas.add(r["cedula"])

    # (1) Clientes del maestro sin póliza
    for cedula in cedulas_maestro:
        if cedula not in cedulas_en_polizas:
            fila = clientes[clientes["Cedula"].astype(str).str.strip() == cedula]
            nombre = ""
            if not fila.empty:
                nombre = fila.iloc[0].get("Nombre_Completo", "")
            inconsistencias.append(
                f"Cliente sin póliza: cédula {cedula} ({nombre})"
            )

    # (2) Pólizas cuya cédula no está en el maestro
    for r in resultados:
        if r["cedula"] and not r["en_maestro"]:
            inconsistencias.append(
                f"Cédula no registrada: póliza {r['numero']} cédula {r['cedula']}"
            )

    # (3) Pólizas sin prima o con fecha ilegible
    for r in resultados:
        if r.get("prima") is None:
            inconsistencias.append(f"Póliza sin prima: {r['numero']}")
        if r.get("hasta") is None:
            inconsistencias.append(f"Póliza con fecha ilegible: {r['numero']}")

    return inconsistencias


def buscar_por_numero(numero, resultados=None):
    """Busca una póliza por su número y devuelve su diccionario de resultados,
    o None si no se encuentra."""
    if resultados is None:
        resultados = calcular_resultados()
    for r in resultados:
        if r["numero"] == numero:
            return r
    return None
