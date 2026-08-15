"""Acceso a datos de la tabla `daily_habits`."""

from datetime import date as date_type
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_habit import DailyHabit


class DailyHabitRepository:
    """Consultas SQL sobre los habitos diarios."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_and_date(self, user_id: int, target_date: date_type) -> DailyHabit | None:
        """Recupera los habitos de un usuario en una fecha concreta.

        Es la consulta que ejecuta el servicio de scoring para cada sesion, y
        se apoya en el indice UNIQUE(user_id, date).
        """
        statement = select(DailyHabit).where(
            DailyHabit.user_id == user_id,
            DailyHabit.date == target_date,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def upsert(
        self,
        user_id: int,
        target_date: date_type,
        caffeine_mg: int,
        last_caffeine_time: time | None,
        exercise_minutes: int,
        screen_time_before_bed_minutes: int,
    ) -> DailyHabit:
        """Crea o actualiza los habitos de un dia.

        Se implementa como SELECT seguido de INSERT/UPDATE en lugar de un
        `INSERT ... ON CONFLICT DO UPDATE` nativo de PostgreSQL. El motivo es de
        arquitectura: el ON CONFLICT ata el repositorio al dialecto de
        PostgreSQL, y aqui la diferencia de una consulta extra es irrelevante
        (la operacion la dispara un humano rellenando un formulario, no un
        proceso masivo). La restriccion UNIQUE(user_id, date) sigue siendo la
        garantia real de unicidad frente a peticiones concurrentes.
        """
        existing = self.get_by_user_and_date(user_id, target_date)

        if existing is not None:
            existing.caffeine_mg = caffeine_mg
            existing.last_caffeine_time = last_caffeine_time
            existing.exercise_minutes = exercise_minutes
            existing.screen_time_before_bed_minutes = screen_time_before_bed_minutes
            self.db.flush()
            return existing

        habit = DailyHabit(
            user_id=user_id,
            date=target_date,
            caffeine_mg=caffeine_mg,
            last_caffeine_time=last_caffeine_time,
            exercise_minutes=exercise_minutes,
            screen_time_before_bed_minutes=screen_time_before_bed_minutes,
        )
        self.db.add(habit)
        self.db.flush()
        return habit

    def create_many(self, habits: list[DailyHabit]) -> list[DailyHabit]:
        """Inserta varios registros de habitos en una sola ida a la base de datos.

        Lo usa la siembra de las cuentas de demostracion. A diferencia de
        `upsert`, este metodo asume que ninguna de las fechas existe ya, cosa
        que en ese contexto esta garantizada porque la cuenta acaba de crearse
        y no tiene ningun registro previo.
        """
        self.db.add_all(habits)
        self.db.flush()
        return habits

    def list_for_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DailyHabit]:
        """Historial de habitos, del dia mas reciente al mas antiguo."""
        statement = (
            select(DailyHabit)
            .where(DailyHabit.user_id == user_id)
            .order_by(DailyHabit.date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(statement).scalars().all())

    def list_all_for_user(self, user_id: int) -> list[DailyHabit]:
        """Todos los habitos del usuario, en orden cronologico ascendente.

        Lo consume el servicio de analitica, que necesita emparejar cada sesion
        con los habitos de su fecha para calcular las correlaciones. Cargarlos
        de una vez y construir un diccionario en memoria evita el problema N+1
        de consultar la base de datos una vez por sesion.
        """
        statement = (
            select(DailyHabit)
            .where(DailyHabit.user_id == user_id)
            .order_by(DailyHabit.date.asc())
        )
        return list(self.db.execute(statement).scalars().all())
