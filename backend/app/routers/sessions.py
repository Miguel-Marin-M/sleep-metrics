"""Endpoints de sesiones de sueno.

Ilustra la regla central de la arquitectura en capas: ningun endpoint de este
modulo importa SQLAlchemy ni recibe una `Session` de base de datos. Toda la
interaccion con los datos pasa por el servicio inyectado.
"""

from fastapi import APIRouter, Path, Query, status

from app.core.dependencies import CurrentUser, SessionServiceDep
from app.schemas.sleep_session import SleepSessionCreate, SleepSessionResponse

router = APIRouter(prefix="/sessions", tags=["Sesiones de sueno"])


@router.get(
    "",
    response_model=list[SleepSessionResponse],
    summary="Historial de sesiones del usuario autenticado",
)
def list_sessions(
    current_user: CurrentUser,
    session_service: SessionServiceDep,
    limit: int = Query(default=100, ge=1, le=500, description="Numero maximo de resultados"),
    offset: int = Query(default=0, ge=0, description="Resultados a saltar (paginacion)"),
) -> list[SleepSessionResponse]:
    """Lista las sesiones del usuario, de la mas reciente a la mas antigua.

    Se pagina con `limit`/`offset` aunque el volumen esperado sea bajo (una
    sesion al dia): un endpoint de listado sin cota superior es una fuga de
    memoria latente en cuanto el historial crece.
    """
    return session_service.list_sessions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=SleepSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una sesion de sueno",
)
def create_session(
    payload: SleepSessionCreate,
    current_user: CurrentUser,
    session_service: SessionServiceDep,
) -> SleepSessionResponse:
    """Crea una sesion de sueno y calcula su score en la misma operacion.

    La respuesta ya incluye el score, de modo que el frontend puede mostrarlo
    sin una segunda llamada.
    """
    return session_service.create_session(user_id=current_user.id, payload=payload)


@router.get(
    "/{session_id}",
    response_model=SleepSessionResponse,
    summary="Detalle de una sesion",
)
def get_session(
    current_user: CurrentUser,
    session_service: SessionServiceDep,
    session_id: int = Path(ge=1, description="ID de la sesion"),
) -> SleepSessionResponse:
    """Devuelve una sesion concreta del usuario autenticado.

    Si la sesion pertenece a otro usuario se responde 404 y no 403: un 403
    confirmaria que ese ID existe, permitiendo enumerar los recursos ajenos.
    """
    return session_service.get_session(user_id=current_user.id, session_id=session_id)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una sesion",
)
def delete_session(
    current_user: CurrentUser,
    session_service: SessionServiceDep,
    session_id: int = Path(ge=1, description="ID de la sesion"),
) -> None:
    """Elimina una sesion del usuario y, en cascada, su score asociado.

    Responde 204 sin cuerpo, que es la semantica correcta de un DELETE
    satisfactorio.
    """
    session_service.delete_session(user_id=current_user.id, session_id=session_id)
