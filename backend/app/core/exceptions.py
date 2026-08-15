"""Excepciones de dominio y su traduccion a respuestas HTTP.

La capa de servicios lanza estas excepciones, que son agnosticas del protocolo
(no conocen codigos de estado ni FastAPI). `main.py` registra manejadores que
las convierten en respuestas HTTP.

Esta separacion es la que permite que un servicio sea reutilizable desde un
comando de consola o una tarea programada sin arrastrar dependencias web.
"""


class DomainError(Exception):
    """Base de todos los errores de negocio de la aplicacion."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """El recurso solicitado no existe, o no pertenece al usuario autenticado.

    Se usa deliberadamente el mismo error para "no existe" y "no es tuyo": si
    se distinguieran, la API filtraria la existencia de recursos ajenos (una
    fuga de informacion conocida como enumeracion de recursos).
    """


class ConflictError(DomainError):
    """La operacion choca con el estado actual del sistema.

    Ejemplo: registrar un email que ya tiene cuenta.
    """


class AuthenticationError(DomainError):
    """Las credenciales son invalidas o faltan."""


class ValidationError(DomainError):
    """Los datos son sintacticamente validos pero violan una regla de negocio.

    Ejemplo: `sleep_end` anterior a `sleep_start`. Se distingue de los errores
    de validacion de Pydantic, que son puramente estructurales.
    """
