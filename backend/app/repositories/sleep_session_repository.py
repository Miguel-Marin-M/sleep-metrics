"""Acceso a datos de la tabla `sleep_sessions`."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.sleep_session import SleepSession


class SleepSessionRepository:
    """Consultas SQL sobre las sesiones de sueno.

    Regla transversal de este repositorio: TODA consulta filtra por `user_id`.
    El aislamiento entre usuarios se garantiza aqui, en la capa de datos, y no
    dependiendo de que cada endpoint se acuerde de comprobarlo.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        user_id: int,
        sleep_start: datetime,
        sleep_end: datetime,
        interruptions: int,
        notes: str | None,
    ) -> SleepSession:
        """Inserta una sesion de sueno y devuelve la entidad con su ID."""
        session = SleepSession(
            user_id=user_id,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            interruptions=interruptions,
            notes=notes,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def create_many(self, sessions: list[SleepSession]) -> list[SleepSession]:
        """Inserta varias sesiones en una sola ida a la base de datos.

        Existe para la siembra de las cuentas de demostracion, que crea decenas
        de noches de golpe. Insertarlas uno a uno supondria una ida y vuelta por
        fila; contra una base de datos remota como Supabase eso convertiria un
        par de segundos en una espera perceptible justo en la primera impresion
        que se lleva el visitante.

        SQLAlchemy 2.0 agrupa los INSERT y recupera los IDs generados en la
        misma sentencia, asi que tras el `flush` los objetos ya tienen su clave
        primaria asignada.
        """
        self.db.add_all(sessions)
        self.db.flush()
        return sessions

    def get_by_id_for_user(self, session_id: int, user_id: int) -> SleepSession | None:
        """Recupera una sesion concreta comprobando la propiedad en el WHERE.

        El filtro por user_id forma parte de la consulta y no de una comprobacion
        posterior en Python. La diferencia es de seguridad: aqui es imposible
        que un olvido en la capa superior exponga la sesion de otro usuario.
        """
        statement = select(SleepSession).where(
            SleepSession.id == session_id,
            SleepSession.user_id == user_id,
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def list_for_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SleepSession]:
        """Historial del usuario, de la sesion mas reciente a la mas antigua.

        El ORDER BY coincide exactamente con el indice compuesto
        (user_id, sleep_start DESC), asi que PostgreSQL lo resuelve recorriendo
        el indice y no necesita ordenar en memoria.
        """
        statement = (
            select(SleepSession)
            .where(SleepSession.user_id == user_id)
            .order_by(SleepSession.sleep_start.desc())
            .limit(limit)
            .offset(offset)
        )
        # `.unique()` es obligatorio porque SleepSession.score usa carga eager
        # con JOIN: SQLAlchemy exige deduplicar las entidades resultantes.
        return list(self.db.execute(statement).unique().scalars().all())

    def list_since(self, user_id: int, since: datetime) -> list[SleepSession]:
        """Sesiones cuyo `sleep_start` es igual o posterior a `since`.

        Es la consulta base de todas las ventanas temporales de analytics
        (ultimos 7 dias, ultimos 30 dias).
        """
        statement = (
            select(SleepSession)
            .where(
                SleepSession.user_id == user_id,
                SleepSession.sleep_start >= since,
            )
            .order_by(SleepSession.sleep_start.asc())
        )
        return list(self.db.execute(statement).unique().scalars().all())

    def list_all_for_user(self, user_id: int) -> list[SleepSession]:
        """Historial completo, en orden cronologico ascendente.

        Lo usa el servicio de analitica para calcular medias por dia de la
        semana y correlaciones, que necesitan la serie entera.
        """
        statement = (
            select(SleepSession)
            .where(SleepSession.user_id == user_id)
            .order_by(SleepSession.sleep_start.asc())
        )
        return list(self.db.execute(statement).unique().scalars().all())

    def count_for_user(self, user_id: int) -> int:
        """Numero total de sesiones registradas por el usuario."""
        from sqlalchemy import func

        statement = select(func.count(SleepSession.id)).where(SleepSession.user_id == user_id)
        return self.db.execute(statement).scalar_one()

    def delete_for_user(self, session_id: int, user_id: int) -> bool:
        """Elimina una sesion propiedad del usuario.

        Returns:
            True si se borro una fila, False si no existia o era de otro usuario.

        Se emite un DELETE directo en lugar de cargar la entidad y llamar a
        `session.delete(obj)`: ahorra un SELECT previo. El score asociado
        desaparece por el ON DELETE CASCADE de la llave foranea.
        """
        statement = delete(SleepSession).where(
            SleepSession.id == session_id,
            SleepSession.user_id == user_id,
        )
        result = self.db.execute(statement)
        return result.rowcount > 0
