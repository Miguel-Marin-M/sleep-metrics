"""Endpoints de habitos diarios."""

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, HabitServiceDep
from app.schemas.daily_habit import DailyHabitCreate, DailyHabitResponse

router = APIRouter(prefix="/habits", tags=["Habitos diarios"])


@router.post(
    "",
    response_model=DailyHabitResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar o actualizar los habitos de un dia",
)
def upsert_habits(
    payload: DailyHabitCreate,
    current_user: CurrentUser,
    habit_service: HabitServiceDep,
) -> DailyHabitResponse:
    """Registra los habitos de un dia, o actualiza los ya existentes.

    Devuelve 200 y no 201 de forma deliberada: la operacion es un upsert y no
    siempre crea un recurso nuevo. Emitir 201 cuando en realidad se actualizo
    una fila existente seria mentir sobre lo ocurrido.

    Efecto secundario: recalcula el score de la sesion de sueno de esa noche,
    para que refleje los habitos que se acaban de registrar.
    """
    return habit_service.upsert_habits(user_id=current_user.id, payload=payload)


@router.get(
    "",
    response_model=list[DailyHabitResponse],
    summary="Historial de habitos del usuario autenticado",
)
def list_habits(
    current_user: CurrentUser,
    habit_service: HabitServiceDep,
    limit: int = Query(default=100, ge=1, le=500, description="Numero maximo de resultados"),
    offset: int = Query(default=0, ge=0, description="Resultados a saltar (paginacion)"),
) -> list[DailyHabitResponse]:
    """Lista los habitos registrados, del dia mas reciente al mas antiguo."""
    return habit_service.list_habits(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
