"""Schemas Pydantic de los endpoints de analitica y scoring."""

from datetime import datetime

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    """Aportacion de un unico factor al score total.

    Devolver el desglose y no solo el numero final es lo que hace accionable la
    metrica: el usuario ve exactamente que le esta restando puntos.
    """

    name: str = Field(description="Nombre legible del componente")
    points: float = Field(description="Puntos obtenidos en este componente")
    max_points: float = Field(description="Puntos maximos posibles del componente")
    detail: str = Field(description="Explicacion en lenguaje natural del calculo")


class SessionScoreResponse(BaseModel):
    """Respuesta de GET /analytics/score/{session_id}."""

    session_id: int
    score: float = Field(ge=0, le=100, description="Score de calidad global 0-100")
    calculated_at: datetime

    components: list[ScoreComponent] = Field(description="Desglose por factor")

    # False cuando no habia habitos registrados para la fecha de la sesion. En
    # ese caso el score se normaliza sobre los dos componentes disponibles.
    habits_available: bool = Field(
        description="Si existian habitos registrados para la fecha de la sesion"
    )

    duration_hours: float


class WeekdayAverage(BaseModel):
    """Promedio de score de un dia de la semana."""

    weekday: int = Field(ge=0, le=6, description="0=lunes ... 6=domingo")
    weekday_name: str
    average_score: float
    sessions_count: int


class PeriodAverage(BaseModel):
    """Promedio de horas dormidas en una ventana temporal."""

    days: int = Field(description="Tamano de la ventana en dias")
    average_hours: float | None = Field(description="Media de horas; None si no hay datos")
    sessions_count: int


class Correlation(BaseModel):
    """Correlacion lineal entre un habito y el score de sueno.

    Se usa el coeficiente de Pearson, en el rango [-1, 1]:
      -1  relacion inversa perfecta (mas habito, menos score)
       0  sin relacion lineal
      +1  relacion directa perfecta
    """

    factor: str = Field(description="Habito analizado")
    coefficient: float | None = Field(
        description="Coeficiente de Pearson; None si no hay muestras suficientes"
    )
    sample_size: int = Field(description="Numero de pares (habito, score) analizados")
    interpretation: str = Field(description="Lectura en lenguaje natural del coeficiente")


class AnalyticsSummary(BaseModel):
    """Respuesta de GET /analytics/summary."""

    total_sessions: int

    # Promedios de horas dormidas en las ventanas de 7 y 30 dias.
    last_7_days: PeriodAverage
    last_30_days: PeriodAverage

    average_score: float | None = Field(description="Score medio historico; None si no hay datos")

    best_weekday: WeekdayAverage | None = Field(description="Dia con mejor score medio")
    worst_weekday: WeekdayAverage | None = Field(description="Dia con peor score medio")

    correlations: list[Correlation]
