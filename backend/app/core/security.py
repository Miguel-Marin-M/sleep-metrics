"""Primitivas de seguridad: hashing de contrasenas y emision/verificacion de JWT.

Este modulo no conoce ni la base de datos ni el framework web: recibe y
devuelve tipos primitivos. Eso lo hace trivial de razonar y de probar.
"""

import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import settings

logger = logging.getLogger("sleepmetrics.security")

# ---------------------------------------------------------------------------
# Hashing de contrasenas
# ---------------------------------------------------------------------------
# bcrypt es un algoritmo de derivacion lento por diseno: encarece los ataques
# de fuerza bruta sobre la base de datos si esta llegara a filtrarse. passlib
# gestiona el salt aleatorio por contrasena de forma automatica, por lo que dos
# usuarios con la misma contrasena producen hashes distintos.
#
# `deprecated="auto"` habilita la migracion transparente de algoritmos: si en
# el futuro se anade un esquema mas fuerte a la lista, passlib marcara los
# hashes bcrypt como obsoletos y podran re-hashearse en el siguiente login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt trunca silenciosamente cualquier entrada mas alla de 72 bytes. El
# limite se valida en los schemas Pydantic para que el usuario reciba un error
# claro en vez de una truncacion invisible que debilitaria su contrasena.
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba una contrasena contra su hash.

    passlib realiza la comparacion en tiempo constante, lo que evita filtrar
    informacion sobre el hash mediante ataques de temporizacion.

    SOBRE EL ALCANCE DEL `except`
    -----------------------------
    Solo se captura `UnknownHashError`, que significa exactamente una cosa: el
    valor almacenado en la columna no tiene formato de hash reconocible. Ese
    caso si equivale a "estas credenciales no sirven" y devolver False es
    correcto.

    Cualquier otro error se deja PROPAGAR a proposito, para que se convierta en
    un 500 con su traza en el log. La version anterior capturaba `ValueError`
    entero, que es la clase padre, y eso enmascaraba fallos de configuracion del
    backend de bcrypt haciendolos pasar por "contrasena incorrecta". El sintoma
    resultante era desconcertante: un servidor con passlib en mal estado
    respondia 401 a credenciales perfectamente validas, y toda la investigacion
    apuntaba a la contrasena o a la base de datos en lugar de al proceso.

    Un error de infraestructura debe parecer un error de infraestructura.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        # El hash guardado no es interpretable (columna corrupta o migrada
        # desde otro esquema de cifrado). No es un fallo del servidor.
        logger.warning("Hash de contrasena con formato no reconocible en la base de datos.")
        return False


# ---------------------------------------------------------------------------
# JSON Web Tokens
# ---------------------------------------------------------------------------

def create_access_token(subject: int, expires_delta: timedelta | None = None) -> str:
    """Genera un access token JWT firmado para un usuario.

    Args:
        subject: ID del usuario. Se guarda en el claim estandar `sub`.
        expires_delta: vigencia personalizada. Por defecto usa
            ACCESS_TOKEN_EXPIRE_MINUTES de la configuracion.

    Claims incluidos:
        sub: identificador del sujeto (ID de usuario, como cadena porque el
             estandar JWT define `sub` como string).
        exp: instante de expiracion. python-jose lo valida automaticamente al
             decodificar y lanza ExpiredSignatureError si ya paso.
        iat: instante de emision, util para auditoria y depuracion.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Verifica la firma y la vigencia de un token y devuelve el ID de usuario.

    Returns:
        El ID de usuario si el token es valido; None si la firma no cuadra, el
        token expiro o el claim `sub` no es un entero.

    Devolver None en lugar de propagar la excepcion mantiene este modulo libre
    de detalles HTTP: es la capa de dependencias la que decide traducir el
    fallo a un 401.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        # Cubre firma invalida, token expirado y JWT malformado.
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
