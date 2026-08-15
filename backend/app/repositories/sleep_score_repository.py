"""Acceso a datos de la tabla `sleep_scores`."""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sleep_score import SleepScore


class SleepScoreRepository:
    """Consultas SQL sobre los scores calculados."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, session_id: int) -> SleepScore | None:
        """Recupera el score vigente de una sesion.

        No filtra por user_id porque no lo necesita: la unica forma de llegar
        aqui es con un session_id que la capa de servicios ya valido como
        propiedad del usuario autenticado.
        """
        statement = select(SleepScore).where(SleepScore.session_id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create_many(self, scores: list[tuple[int, float]]) -> list[SleepScore]:
        """Inserta varios scores en una sola ida a la base de datos.

        Args:
            scores: pares (session_id, score).

        Lo usa la siembra de las cuentas de demostracion. Asume que ninguna de
        esas sesiones tiene score todavia, cosa garantizada porque se acaban de
        crear en la misma transaccion.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        rows = [
            SleepScore(
                session_id=session_id,
                score=Decimal(str(score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                calculated_at=now,
            )
            for session_id, score in scores
        ]

        self.db.add_all(rows)
        self.db.flush()
        return rows

    def upsert(self, session_id: int, score: float) -> SleepScore:
        """Guarda o actualiza el score de una sesion.

        La relacion es 1:1 (UNIQUE sobre session_id), asi que recalcular
        sobrescribe la fila existente en vez de acumular historico. Tambien se
        refresca `calculated_at` para dejar constancia del ultimo recalculo.
        """
        # Se convierte a Decimal con la escala exacta de la columna NUMERIC(5,2)
        # antes de persistir. Dejar que el driver convierta un float arrastraria
        # el ruido binario de la representacion en coma flotante.
        quantized = Decimal(str(score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        existing = self.get_by_session_id(session_id)

        if existing is not None:
            existing.score = quantized
            # naive UTC, coherente con las columnas TIMESTAMP sin zona horaria.
            existing.calculated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.db.flush()
            return existing

        sleep_score = SleepScore(
            session_id=session_id,
            score=quantized,
            calculated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(sleep_score)
        self.db.flush()
        return sleep_score
