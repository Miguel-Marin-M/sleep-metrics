"""Capa de repositorios: unico punto del sistema que ejecuta SQL.

Su razon de ser es aislar SQLAlchemy del resto de la aplicacion. Los servicios
piden datos en terminos del dominio ("las sesiones de este usuario desde esta
fecha") sin conocer `select()`, joins ni sesiones del ORM.

Convenciones de la capa:
  - Reciben la `Session` por constructor; nunca la crean.
  - Hacen `flush()` para obtener los IDs generados, pero NUNCA `commit()`: el
    limite transaccional pertenece a la capa de servicios.
  - Devuelven modelos SQLAlchemy o None; nunca lanzan excepciones HTTP.
  - Toda consulta de datos de usuario filtra por `user_id` dentro del WHERE.
"""

from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "SleepSessionRepository",
    "DailyHabitRepository",
    "SleepScoreRepository",
]
