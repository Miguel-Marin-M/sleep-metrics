"""Schemas Pydantic de la entidad usuario."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Representacion publica de un usuario.

    Este schema es la frontera de seguridad de la entidad: `password_hash` no
    esta declarado aqui, por lo que es literalmente imposible que se filtre en
    una respuesta HTTP aunque el modelo ORM lo lleve dentro.
    """

    # from_attributes permite construir el schema directamente desde el objeto
    # SQLAlchemy (leyendo atributos en vez de claves de diccionario).
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime

    # Permite al frontend mostrar el aviso de cuenta de demostracion y explicar
    # que los datos son ficticios y temporales. Se expone porque es informacion
    # que el usuario debe conocer, no un detalle interno.
    is_demo: bool = False


class UserPublic(BaseModel):
    """Datos minimos del usuario para el contexto de sesion del frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(description="Nombre para mostrar en la interfaz")
    email: EmailStr
