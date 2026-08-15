"""Schemas Pydantic de los habitos diarios."""

from datetime import date as date_type
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DailyHabitCreate(BaseModel):
    """Cuerpo de POST /habits.

    El endpoint tiene semantica de UPSERT: si ya existen habitos registrados
    para ese usuario y esa fecha, se actualizan. Es el comportamiento natural
    del dominio, donde el usuario va completando los datos del dia a lo largo
    de la jornada, y se apoya en la restriccion UNIQUE(user_id, date).
    """

    date: date_type = Field(
        description=(
            "Dia de la NOCHE a la que corresponden los habitos. Acostarse "
            "despues de medianoche sigue perteneciendo a la noche del dia "
            "anterior: dormirse a las 00:30 del sabado es la noche del viernes."
        )
    )

    caffeine_mg: int = Field(
        default=0,
        ge=0,
        le=2000,
        description="Cafeina total del dia en mg (una taza de cafe ~95 mg)",
    )

    last_caffeine_time: time | None = Field(
        default=None,
        description=(
            "Hora del ultimo consumo de cafeina (HH:MM). Opcional: si se omite, "
            "el calculo del score aplica un factor de proximidad conservador."
        ),
    )

    exercise_minutes: int = Field(default=0, ge=0, le=1440)

    screen_time_before_bed_minutes: int = Field(
        default=0,
        ge=0,
        le=1440,
        description="Minutos de pantalla en la hora previa a acostarse",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "DailyHabitCreate":
        """Reglas de coherencia entre campos."""
        # Registrar una hora de consumo con 0 mg de cafeina es contradictorio.
        # Se limpia en vez de rechazarse: la intencion del usuario es clara.
        if self.caffeine_mg == 0:
            self.last_caffeine_time = None

        # Rechaza fechas futuras: no se pueden registrar habitos que aun no han
        # ocurrido, y admitirlas ensuciaria las agregaciones de analytics.
        if self.date > datetime.now().date():
            raise ValueError("No se pueden registrar habitos con fecha futura.")

        return self


class DailyHabitResponse(BaseModel):
    """Habitos diarios tal como los devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date_type
    caffeine_mg: int
    last_caffeine_time: time | None
    exercise_minutes: int
    screen_time_before_bed_minutes: int
    created_at: datetime
