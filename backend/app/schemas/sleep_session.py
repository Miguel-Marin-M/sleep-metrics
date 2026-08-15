"""Schemas Pydantic de las sesiones de sueno."""

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Limite superior de duracion. Coincide con el CHECK constraint de la tabla:
# una sesion de mas de 24 horas es casi con seguridad un error de captura.
MAX_SESSION_DURATION = timedelta(hours=24)

# Limite inferior: menos de 30 minutos no es una noche de sueno registrable.
MIN_SESSION_DURATION = timedelta(minutes=30)


class SleepSessionCreate(BaseModel):
    """Cuerpo de POST /sessions.

    Las marcas de tiempo se reciben en formato ISO 8601 SIN offset de zona
    horaria (ejemplo: "2026-08-14T23:30:00"), porque la aplicacion trabaja con
    hora local del usuario: el dominio del sueno es local por naturaleza.
    """

    sleep_start: datetime = Field(description="Momento de acostarse (hora local, sin zona)")
    sleep_end: datetime = Field(description="Momento de despertar (hora local, sin zona)")

    interruptions: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Numero de despertares durante la noche",
    )

    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_interval(self) -> "SleepSessionCreate":
        """Valida la coherencia del intervalo antes de que llegue al servicio.

        Es una validacion estructural, no de negocio: cualquier consumidor de
        la API debe cumplirla siempre. Las reglas que dependen del estado del
        sistema viven en la capa de servicios.
        """
        # Un datetime con zona horaria mezclado con los naive de la base de
        # datos produciria comparaciones invalidas mas adelante. Se normaliza
        # descartando el offset y quedandose con la hora de pared.
        if self.sleep_start.tzinfo is not None:
            self.sleep_start = self.sleep_start.replace(tzinfo=None)
        if self.sleep_end.tzinfo is not None:
            self.sleep_end = self.sleep_end.replace(tzinfo=None)

        if self.sleep_end <= self.sleep_start:
            raise ValueError("sleep_end debe ser posterior a sleep_start.")

        duration = self.sleep_end - self.sleep_start
        if duration > MAX_SESSION_DURATION:
            raise ValueError("Una sesion de sueno no puede durar mas de 24 horas.")
        if duration < MIN_SESSION_DURATION:
            raise ValueError("Una sesion de sueno debe durar al menos 30 minutos.")

        if self.notes is not None:
            cleaned = self.notes.strip()
            self.notes = cleaned or None

        return self


class SleepSessionResponse(BaseModel):
    """Sesion de sueno tal como la devuelve la API.

    Incluye dos campos derivados que el frontend necesitaria calcular en cada
    render: la duracion en horas y el score. Servirlos desde el backend
    mantiene una unica implementacion de esa logica.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    sleep_start: datetime
    sleep_end: datetime
    interruptions: int
    notes: str | None
    created_at: datetime

    duration_hours: float = Field(description="Duracion en horas decimales")

    # None solo si el score aun no se ha calculado; en la practica siempre
    # viene relleno porque POST /sessions lo calcula al crear la sesion.
    score: float | None = Field(default=None, description="Score de calidad 0-100")
