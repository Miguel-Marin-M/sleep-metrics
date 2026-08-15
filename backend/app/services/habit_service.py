"""Logica de negocio de los habitos diarios."""

from app.models.daily_habit import DailyHabit
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.schemas.daily_habit import DailyHabitCreate, DailyHabitResponse
from app.services.night import night_date
from app.services.scoring_service import calculate_sleep_score


class HabitService:
    """Casos de uso sobre habitos diarios.

    Depende tambien de los repositorios de sesiones y scores por una razon de
    dominio: registrar los habitos de un dia cambia el score de la noche que
    empieza ese dia, y ese score debe reflejarlo sin intervencion del usuario.
    """

    def __init__(
        self,
        habit_repository: DailyHabitRepository,
        session_repository: SleepSessionRepository,
        score_repository: SleepScoreRepository,
    ) -> None:
        self.habit_repository = habit_repository
        self.session_repository = session_repository
        self.score_repository = score_repository

    def upsert_habits(self, user_id: int, payload: DailyHabitCreate) -> DailyHabitResponse:
        """Registra o actualiza los habitos de un dia.

        Es un UPSERT y no un INSERT porque el usuario completa los datos del dia
        de forma incremental: el cafe de la manana se anota antes que el tiempo
        de pantalla de la noche. Un INSERT puro obligaria a distinguir entre
        crear y editar en la interfaz sin aportar nada.

        Efecto secundario intencional: recalcula el score de las sesiones de
        sueno afectadas por estos habitos.
        """
        habit = self.habit_repository.upsert(
            user_id=user_id,
            target_date=payload.date,
            caffeine_mg=payload.caffeine_mg,
            last_caffeine_time=payload.last_caffeine_time,
            exercise_minutes=payload.exercise_minutes,
            screen_time_before_bed_minutes=payload.screen_time_before_bed_minutes,
        )

        self._refresh_affected_scores(user_id=user_id, habit=habit)

        # Un unico commit para el upsert de habitos y el recalculo de scores.
        self.habit_repository.db.commit()

        return DailyHabitResponse.model_validate(habit)

    def list_habits(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DailyHabitResponse]:
        """Historial de habitos del usuario, del dia mas reciente al mas antiguo."""
        habits = self.habit_repository.list_for_user(user_id, limit=limit, offset=offset)
        return [DailyHabitResponse.model_validate(habit) for habit in habits]

    # -----------------------------------------------------------------------
    # Helpers internos
    # -----------------------------------------------------------------------

    def _refresh_affected_scores(self, user_id: int, habit: DailyHabit) -> None:
        """Recalcula el score de las sesiones asociadas a la fecha de `habit`.

        Sin esto, el score quedaria desactualizado en el flujo mas frecuente de
        la aplicacion: registrar la sesion al despertar y los habitos del dia
        mas tarde. El usuario veria un score calculado sin el componente de
        habitos que acaba de introducir.

        Se recorren todas las sesiones del usuario en memoria en lugar de
        anadir una consulta por rango de fechas al repositorio. Es una decision
        consciente: el volumen por usuario es de una sesion al dia, y la
        alternativa cargaria la interfaz del repositorio con un metodo que solo
        usaria este caso. Si el volumen creciera, aqui es donde habria que
        introducir un `list_by_date` filtrado en SQL.
        """
        sessions = self.session_repository.list_all_for_user(user_id)

        for session in sessions:
            # Se compara con la NOCHE de la sesion, no con la fecha cruda de
            # sleep_start: acostarse a las 00:05 del sabado pertenece a la
            # noche del viernes. Ver `app.services.night`.
            if night_date(session.sleep_start) != habit.date:
                continue

            score_result = calculate_sleep_score(session=session, habit=habit)
            self.score_repository.upsert(session_id=session.id, score=score_result.score)
