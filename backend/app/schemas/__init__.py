"""Capa de schemas: contratos de entrada y salida de la API (Pydantic v2).

Los schemas son la frontera publica de la aplicacion. Estan deliberadamente
separados de los modelos SQLAlchemy: un modelo describe COMO se almacena una
entidad, un schema describe QUE se expone de ella. Mezclarlos acaba filtrando
columnas internas (por ejemplo `password_hash`) en las respuestas HTTP.
"""

from app.schemas.analytics import (
    AnalyticsSummary,
    Correlation,
    PeriodAverage,
    ScoreComponent,
    SessionScoreResponse,
    WeekdayAverage,
)
from app.schemas.auth import AuthResponse, LoginRequest, MessageResponse, RegisterRequest
from app.schemas.daily_habit import DailyHabitCreate, DailyHabitResponse
from app.schemas.sleep_session import SleepSessionCreate, SleepSessionResponse
from app.schemas.user import UserPublic, UserResponse

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "AuthResponse",
    "MessageResponse",
    "UserResponse",
    "UserPublic",
    "SleepSessionCreate",
    "SleepSessionResponse",
    "DailyHabitCreate",
    "DailyHabitResponse",
    "ScoreComponent",
    "SessionScoreResponse",
    "WeekdayAverage",
    "PeriodAverage",
    "Correlation",
    "AnalyticsSummary",
]
