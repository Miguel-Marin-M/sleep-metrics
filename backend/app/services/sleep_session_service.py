"""Logica de negocio de las sesiones de sueno."""

from app.core.exceptions import NotFoundError
from app.models.sleep_session import SleepSession
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.schemas.sleep_session import SleepSessionCreate, SleepSessionResponse
from app.services.night import night_date
from app.services.scoring_service import ScoreResult, calculate_sleep_score


class SleepSessionService:
    """Casos de uso sobre sesiones de sueno: crear, consultar, listar, borrar.

    Coordina tres repositorios porque una sesion de sueno no vive aislada: al
    crearse necesita los habitos del dia para calcular su score y necesita
    persistir ese score. Esa coordinacion es exactamente la responsabilidad de
    la capa de servicios.
    """

    def __init__(
        self,
        session_repository: SleepSessionRepository,
        habit_repository: DailyHabitRepository,
        score_repository: SleepScoreRepository,
    ) -> None:
        self.session_repository = session_repository
        self.habit_repository = habit_repository
        self.score_repository = score_repository

    # -----------------------------------------------------------------------
    # Casos de uso
    # -----------------------------------------------------------------------

    def create_session(self, user_id: int, payload: SleepSessionCreate) -> SleepSessionResponse:
        """Registra una sesion de sueno y calcula su score de inmediato.

        El score se calcula al crear (y no bajo demanda) para que el historial y
        el dashboard puedan mostrarlo en una sola consulta, sin disparar un
        calculo por fila.
        """
        session = self.session_repository.create(
            user_id=user_id,
            sleep_start=payload.sleep_start,
            sleep_end=payload.sleep_end,
            interruptions=payload.interruptions,
            notes=payload.notes,
        )

        score_result = self._compute_and_store_score(session)

        # Un unico commit cierra la transaccion que contiene el INSERT de la
        # sesion y el de su score: o se guardan ambos o no se guarda ninguno.
        self.session_repository.db.commit()

        return self._to_response(session, score_result.score)

    def get_session(self, user_id: int, session_id: int) -> SleepSessionResponse:
        """Recupera una sesion concreta del usuario autenticado.

        Raises:
            NotFoundError: si no existe o pertenece a otro usuario.
        """
        session = self.session_repository.get_by_id_for_user(session_id, user_id)
        if session is None:
            raise NotFoundError("Sesion de sueno no encontrada.")

        score = float(session.score.score) if session.score is not None else None
        return self._to_response(session, score)

    def list_sessions(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SleepSessionResponse]:
        """Historial del usuario, de la sesion mas reciente a la mas antigua."""
        sessions = self.session_repository.list_for_user(user_id, limit=limit, offset=offset)
        return [
            self._to_response(
                session,
                float(session.score.score) if session.score is not None else None,
            )
            for session in sessions
        ]

    def delete_session(self, user_id: int, session_id: int) -> None:
        """Elimina una sesion del usuario.

        El score asociado se borra en cascada por la llave foranea.

        Raises:
            NotFoundError: si no existe o pertenece a otro usuario.
        """
        deleted = self.session_repository.delete_for_user(session_id, user_id)
        if not deleted:
            # No se hace commit: no hubo cambios que confirmar.
            raise NotFoundError("Sesion de sueno no encontrada.")

        self.session_repository.db.commit()

    def recalculate_score(self, user_id: int, session_id: int) -> tuple[SleepSession, ScoreResult]:
        """Recalcula el score de una sesion y persiste el resultado.

        Existe porque el orden de captura no esta garantizado: es habitual
        registrar la sesion al despertar y los habitos del dia mas tarde. Sin
        recalculo, ese score quedaria congelado sin el componente de habitos.

        Returns:
            La sesion y el resultado detallado del calculo, que el servicio de
            analitica convierte en la respuesta del endpoint.

        Raises:
            NotFoundError: si la sesion no existe o pertenece a otro usuario.
        """
        session = self.session_repository.get_by_id_for_user(session_id, user_id)
        if session is None:
            raise NotFoundError("Sesion de sueno no encontrada.")

        score_result = self._compute_and_store_score(session)
        self.session_repository.db.commit()

        return session, score_result

    # -----------------------------------------------------------------------
    # Helpers internos
    # -----------------------------------------------------------------------

    def _compute_and_store_score(self, session: SleepSession) -> ScoreResult:
        """Calcula el score de una sesion y lo guarda (sin cerrar transaccion).

        Los habitos se buscan por la NOCHE a la que pertenece la sesion, que no
        siempre coincide con la fecha de `sleep_start`: acostarse a las 00:05
        del sabado es la noche del viernes. La regla completa y su justificacion
        estan en `app.services.night`.
        """
        habit = self.habit_repository.get_by_user_and_date(
            user_id=session.user_id,
            target_date=night_date(session.sleep_start),
        )

        score_result = calculate_sleep_score(session=session, habit=habit)

        self.score_repository.upsert(session_id=session.id, score=score_result.score)

        return score_result

    @staticmethod
    def _to_response(session: SleepSession, score: float | None) -> SleepSessionResponse:
        """Convierte el modelo ORM en el schema de respuesta.

        El score llega como parametro explicito en lugar de leerse de
        `session.score`: tras un upsert reciente esa relacion puede estar
        desactualizada en la sesion de SQLAlchemy, y pasarlo a mano elimina la
        ambiguedad.
        """
        return SleepSessionResponse(
            id=session.id,
            user_id=session.user_id,
            sleep_start=session.sleep_start,
            sleep_end=session.sleep_end,
            interruptions=session.interruptions,
            notes=session.notes,
            created_at=session.created_at,
            duration_hours=round(session.duration_hours, 2),
            score=score,
        )
