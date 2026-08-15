#!/usr/bin/env bash
# ===========================================================================
# SleepMetrics - Script de arranque del backend en produccion (Render)
#
# Es el "Start Command" del servicio en Render:
#
#     bash start.sh
#
# Resuelve el requisito de aplicar las migraciones pendientes ANTES de que el
# servidor acepte la primera peticion.
#
# POR QUE UN SCRIPT Y NO EL EVENTO lifespan DE FASTAPI
# -----------------------------------------------------
# Migrar dentro del lifespan de la aplicacion parece mas comodo, pero tiene dos
# problemas reales:
#
#   1. Concurrencia. Render puede arrancar varias instancias (o solapar la
#      antigua y la nueva durante un despliegue sin cortes). Si cada proceso
#      migrara en su propio lifespan, competirian por el mismo lock de Alembic.
#      Un paso previo y separado ocurre una unica vez por despliegue.
#
#   2. Diagnostico. Con `set -e`, una migracion fallida aborta el arranque y el
#      despliegue queda marcado como fallido en Render, con el error visible en
#      el log. Dentro del lifespan, el fallo quedaria sepultado y el servicio
#      podria acabar sirviendo trafico contra un schema incorrecto.
# ===========================================================================

# -e  aborta al primer comando que falle: si la migracion falla, el servidor
#     NO arranca. Es exactamente lo que se quiere.
# -u  aborta si se usa una variable no definida.
# -o pipefail  propaga el fallo de cualquier comando dentro de una tuberia.
set -euo pipefail

echo "==> SleepMetrics: iniciando despliegue del backend"

# ---------------------------------------------------------------------------
# Paso 1: aplicar las migraciones pendientes
#
# `alembic upgrade head` es idempotente: compara la tabla alembic_version de la
# base de datos con las revisiones disponibles y aplica solo lo que falte. Si
# no hay nada pendiente, no hace nada y termina con codigo 0.
# ---------------------------------------------------------------------------
echo "==> Aplicando migraciones de base de datos (alembic upgrade head)..."
alembic upgrade head
echo "==> Migraciones aplicadas correctamente."

# ---------------------------------------------------------------------------
# Paso 2: purgar las cuentas de demostracion caducadas
#
# Las cuentas desechables que genera POST /auth/demo ya se limpian solas al
# crear una nueva, pero eso solo ocurre si hay visitas. Este paso garantiza un
# suelo minimo de mantenimiento aunque el portafolio pase semanas sin trafico.
#
# El script devuelve siempre 0, incluso si falla: un error de limpieza no es
# motivo para abortar el despliegue y dejar la API caida. Aun asi se anade
# `|| true` como red de seguridad, porque `set -e` esta activo y un fallo
# inesperado del interprete (no del script) tumbaria el arranque.
# ---------------------------------------------------------------------------
echo "==> Purgando cuentas de demostracion caducadas..."
python -m scripts.purge_demo_accounts || true

# ---------------------------------------------------------------------------
# Paso 3: levantar el servidor
#
# `exec` sustituye el proceso del shell por el de uvicorn, en lugar de dejarlo
# como proceso hijo. Importa porque asi uvicorn recibe directamente el SIGTERM
# que Render envia al reiniciar el servicio y puede cerrar de forma ordenada.
#
# --workers 1 es intencional en el free tier: 512 MB de RAM no dan para varios
# procesos, y cada worker abriria su propio pool de conexiones contra el limite
# de conexiones del free tier de Supabase.
#
# $PORT lo inyecta Render; el valor por defecto solo aplica en local.
# ---------------------------------------------------------------------------
echo "==> Levantando servidor uvicorn en el puerto ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips="*"
