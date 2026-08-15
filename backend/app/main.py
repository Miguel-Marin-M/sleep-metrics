"""Punto de entrada de la aplicacion FastAPI.

Aqui se ensambla todo: middleware, manejadores de excepciones y registro de
routers. Es tambien la unica capa que traduce las excepciones de dominio a
codigos de estado HTTP, de forma que los servicios permanezcan agnosticos del
protocolo.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.routers import analytics_router, auth_router, habits_router, sessions_router

logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sleepmetrics")


# ---------------------------------------------------------------------------
# Ciclo de vida de la aplicacion
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Comprueba la conectividad con la base de datos en el arranque.

    Fallar rapido y con un mensaje claro aqui es mucho mejor que dejar que la
    aplicacion arranque y que cada peticion falle por separado con un error de
    conexion enterrado en el log.

    Las MIGRACIONES NO se ejecutan aqui, sino en `start.sh`, ANTES de levantar
    el proceso del servidor. El motivo es que Render puede escalar a varias
    instancias del servicio: si cada proceso aplicara migraciones en su propio
    lifespan, varias instancias competirian por el mismo lock de Alembic. Un
    paso previo y separado al arranque del servidor evita esa carrera.
    """
    logger.info("Iniciando SleepMetrics API (entorno: %s)", settings.ENVIRONMENT)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Conexion con la base de datos verificada.")
    except SQLAlchemyError as exc:
        logger.error("No se pudo conectar con la base de datos: %s", exc)
        # No se relanza la excepcion: en Render, un fallo transitorio del
        # pooler de Supabase durante el arranque tumbaria el despliegue entero.
        # `pool_pre_ping` recuperara la conexion en cuanto vuelva a estar
        # disponible, y el endpoint /health reportara el estado real mientras
        # tanto.

    yield

    logger.info("Cerrando SleepMetrics API.")
    engine.dispose()


# ---------------------------------------------------------------------------
# Instancia de la aplicacion
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SleepMetrics API",
    description=(
        "API de analisis de patrones de sueno. Registra sesiones de sueno y "
        "habitos diarios, calcula un score de calidad de 0 a 100 y expone "
        "metricas agregadas y correlaciones entre habitos y descanso."
    ),
    version="1.0.0",
    lifespan=lifespan,
    # La documentacion interactiva se desactiva en produccion: publica el mapa
    # completo de la superficie de ataque de la API sin necesidad alguna.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware de CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    # Origenes exactos, nunca "*": la especificacion de CORS prohibe el comodin
    # cuando se permiten credenciales, y aqui son imprescindibles porque la
    # sesion viaja en cookie.
    allow_origins=settings.cors_origins,
    # Autoriza al navegador a enviar y recibir cookies en peticiones cross-site.
    # Sin esto, la cookie de sesion jamas llegaria desde Vercel hasta Render.
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    # Cachea la respuesta al preflight OPTIONS durante 10 minutos y reduce el
    # numero de idas y venidas extra en la red.
    max_age=600,
)


# ---------------------------------------------------------------------------
# Manejadores de excepciones
#
# Traducen las excepciones de dominio (agnosticas del protocolo) a respuestas
# HTTP. Es la razon de que la capa de servicios pueda lanzar `NotFoundError` en
# lugar de `HTTPException` y siga siendo reutilizable fuera de una API web.
# ---------------------------------------------------------------------------

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Recurso inexistente o ajeno al usuario autenticado."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Conflicto con el estado actual (por ejemplo, email ya registrado)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


@app.exception_handler(AuthenticationError)
async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Credenciales invalidas."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Regla de negocio violada.

    Se responde 422 y no 400 para alinearse con el codigo que FastAPI usa en
    los errores de validacion de Pydantic: el cliente recibe el mismo estado
    tanto si el fallo es estructural como si es de negocio.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Violacion de una restriccion de la base de datos.

    Es la red de seguridad frente a condiciones de carrera: dos peticiones
    simultaneas pueden superar ambas la comprobacion previa de "email ya
    existe" y chocar despues contra la restriccion UNIQUE. Sin este manejador
    el usuario recibiria un 500 opaco en vez de un 409 con sentido.
    """
    logger.warning("Violacion de integridad en %s: %s", request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "La operacion entra en conflicto con datos ya existentes."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ultima red de seguridad para errores no previstos.

    El detalle real se registra en el log del servidor pero NO se devuelve al
    cliente en produccion: los mensajes de excepcion de Python filtran rutas de
    archivos, nombres de tablas y fragmentos de consultas SQL.
    """
    logger.exception("Error no controlado en %s: %s", request.url.path, exc)

    detail = (
        "Error interno del servidor."
        if settings.is_production
        else f"{type(exc).__name__}: {exc}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


# ---------------------------------------------------------------------------
# Endpoints de infraestructura
# ---------------------------------------------------------------------------

@app.get("/", tags=["Sistema"], summary="Informacion de la API")
def root() -> dict[str, str]:
    """Metadatos basicos del servicio."""
    return {
        "name": "SleepMetrics API",
        "version": "1.0.0",
        "status": "online",
        "docs": "deshabilitada en produccion" if settings.is_production else "/docs",
    }


@app.get("/health", tags=["Sistema"], summary="Comprobacion de salud")
def health_check() -> JSONResponse:
    """Verifica que la API responde y que la base de datos esta accesible.

    Sirve para dos cosas concretas en este despliegue:
      1. Diagnostico: distingue "la API esta caida" de "la base de datos no
         responde", que son incidentes muy distintos.
      2. Mantener despierto el servicio: el free tier de Render suspende una
         instancia tras 15 minutos sin trafico, y el primer arranque en frio
         tarda unos 50 segundos. Un ping periodico a este endpoint desde un
         cron externo evita esa espera al usuario.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
        http_status = status.HTTP_200_OK
    except SQLAlchemyError as exc:
        logger.error("Fallo en la comprobacion de salud de la base de datos: %s", exc)
        database_status = "error"
        # 503 y no 200: un monitor externo debe poder detectar el fallo por el
        # codigo de estado, sin analizar el cuerpo de la respuesta.
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={"api": "ok", "database": database_status},
    )


# ---------------------------------------------------------------------------
# Registro de routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(habits_router)
app.include_router(analytics_router)
