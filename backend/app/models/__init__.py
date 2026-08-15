"""Capa de modelos: definicion de las tablas con SQLAlchemy ORM.

IMPORTANTE: todos los modelos deben importarse aqui.

Alembic construye las migraciones a partir de `Base.metadata`, y una tabla solo
aparece en ese metadata si su modulo llego a ejecutarse. Si un modelo no se
importa en este archivo, `alembic revision --autogenerate` no lo vera y, peor
aun, interpretara su tabla como sobrante y generara un DROP TABLE.
"""

from app.models.base import Base
from app.models.daily_habit import DailyHabit
from app.models.sleep_score import SleepScore
from app.models.sleep_session import SleepSession
from app.models.user import User

__all__ = ["Base", "User", "SleepSession", "DailyHabit", "SleepScore"]
