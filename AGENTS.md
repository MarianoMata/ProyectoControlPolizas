# AGENTS.md

Este no es un proyecto de software. Es una carpeta de entradas de pólizas de seguros. No busques código fuente, pruebas, gestor de paquetes, servidor de desarrollo, CI ni comandos de compilación — ninguno existe aquí.

## Contenido

- `Insumos_Control_Polizas/Maestro_Clientes.xlsx` — hoja maestra de clientes.
- `Insumos_Control_Polizas/polizas/` — archivos PDF de pólizas, nombrados `Poliza_<TIPO>-<ANO>-<SEQ>.pdf`:
  - TIPO ∈ {AIS, PCS, SPC} (ej. `Poliza_AIS-2026-0001.pdf`, `Poliza_PCS-2026-0008.pdf`, `Poliza_SPC-2026-0003.pdf`)
  - ANO es el año (ej. `2026`); SEQ es un número de secuencia con relleno de ceros.
- Ignora los archivos `.DS_Store` (metadatos de macOS) en la raíz del repositorio y bajo `Insumos_Control_Polizas/` — no son datos.

## Qué un agente NO debe asumir

- No hay `package.json`, `requirements.txt`, `Makefile` ni ningún archivo de configuración de compilación/pruebas/lint.
- No hay pruebas que ejecutar; no hay comandos `test`, `lint`, `typecheck` o `build`.
- No hay puntos de entrada, límites de paquete ni flujo de ejecución.
- No hay flujos de CI, ganchos pre-commit ni servicios requeridos.

## Si vas a agregar código a este repositorio

Decide primero el stack, luego crea el manifiesto y la configuración adecuados. No infieras tooling de este repositorio — no hay ninguno.
