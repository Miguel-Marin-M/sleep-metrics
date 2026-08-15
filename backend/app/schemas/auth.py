"""Schemas Pydantic del flujo de autenticacion."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES
from app.schemas.user import UserResponse


def _validate_password_bytes(value: str) -> str:
    """Rechaza contrasenas que excedan el limite real de bcrypt.

    bcrypt opera sobre 72 BYTES, no 72 caracteres, y trunca en silencio todo lo
    que sobre. Una contrasena de 80 caracteres se guardaria como sus primeros
    72 bytes sin que el usuario lo supiera, debilitandola sin aviso. Se valida
    en bytes UTF-8 porque un caracter acentuado ocupa 2 bytes y un emoji hasta 4.
    """
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"La contrasena no puede superar {BCRYPT_MAX_PASSWORD_BYTES} bytes "
            "(los caracteres acentuados ocupan mas de un byte)."
        )
    return value


class RegisterRequest(BaseModel):
    """Cuerpo de POST /auth/register."""

    name: str = Field(min_length=2, max_length=120, description="Nombre para mostrar")

    # EmailStr valida el formato del email mediante email-validator.
    email: EmailStr = Field(description="Email de login, unico por cuenta")

    password: str = Field(
        min_length=8,
        max_length=72,
        description="Minimo 8 caracteres",
    )

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return _validate_password_bytes(value)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Normaliza espacios sobrantes y rechaza nombres compuestos solo por
        espacios en blanco, que superarian min_length sin ser validos."""
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres visibles.")
        return cleaned


class LoginRequest(BaseModel):
    """Cuerpo de POST /auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return _validate_password_bytes(value)


class AuthResponse(BaseModel):
    """Respuesta de register y login.

    NO incluye el access token en el cuerpo a proposito: el JWT viaja en una
    cookie httpOnly emitida por el backend, inaccesible para el JavaScript del
    navegador. Devolverlo tambien en el JSON anularia esa proteccion, ya que el
    frontend podria guardarlo en localStorage y volveria a ser robable por XSS.
    """

    user: UserResponse
    message: str = "Autenticacion correcta"


class MessageResponse(BaseModel):
    """Respuesta generica para operaciones sin payload (logout, borrados)."""

    message: str
