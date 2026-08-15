"""Endpoints de analitica y scoring."""

from fastapi import APIRouter, Path

from app.core.dependencies import AnalyticsServiceDep, CurrentUser
from app.schemas.analytics import AnalyticsSummary, SessionScoreResponse

router = APIRouter(prefix="/analytics", tags=["Analitica"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Resumen analitico del historial de sueno",
)
def get_summary(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
) -> AnalyticsSummary:
    """Devuelve las metricas agregadas del usuario.

    Incluye:
      - Promedio de horas dormidas en los ultimos 7 y 30 dias.
      - Score medio historico.
      - Dia de la semana con mejor y con peor score medio.
      - Correlacion de Pearson entre cafeina, tiempo de pantalla y ejercicio
        frente al score de sueno.

    Todas las metricas soportan el caso de historial vacio: devuelven None en
    lugar de fallar, para que un usuario recien registrado vea un dashboard
    coherente en lugar de un error.
    """
    return analytics_service.get_summary(user_id=current_user.id)


@router.get(
    "/score/{session_id}",
    response_model=SessionScoreResponse,
    summary="Calcular el score de calidad de una sesion",
)
def get_session_score(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    session_id: int = Path(ge=1, description="ID de la sesion de sueno"),
) -> SessionScoreResponse:
    """Recalcula el score de una sesion y devuelve su desglose completo.

    Recalcula en lugar de leer el valor almacenado porque los habitos del dia
    pueden haberse registrado despues de crear la sesion. El resultado se
    persiste, asi que el historial queda actualizado con la misma llamada.

    La respuesta detalla la aportacion de cada componente (duracion,
    interrupciones, cafeina, tiempo de pantalla) con su explicacion: es lo que
    convierte el score en informacion accionable y no en un numero opaco.
    """
    return analytics_service.get_session_score(
        user_id=current_user.id,
        session_id=session_id,
    )
