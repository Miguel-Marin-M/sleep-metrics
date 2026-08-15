"""Capa de servicios: la logica de negocio de la aplicacion.

Es el corazon del sistema y la unica capa que conoce las REGLAS del dominio:
como se calcula un score, que hace que un registro de habitos sea valido, que
significa "los ultimos 7 dias".

Convenciones de la capa:
  - Reciben repositorios por constructor (inyeccion de dependencias) y no
    construyen sesiones de base de datos por su cuenta.
  - Son duenos del limite transaccional: aqui se llama a `commit()`.
  - Lanzan excepciones de dominio (`app.core.exceptions`), nunca HTTPException:
    un servicio debe poder ejecutarse fuera de una peticion HTTP.
  - No conocen FastAPI, Request ni Response.
"""

from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.habit_service import HabitService
from app.services.scoring_service import ScoreResult, calculate_sleep_score
from app.services.sleep_session_service import SleepSessionService

__all__ = [
    "AuthService",
    "SleepSessionService",
    "HabitService",
    "AnalyticsService",
    "calculate_sleep_score",
    "ScoreResult",
]
