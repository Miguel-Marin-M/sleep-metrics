"""Cableado de la inyeccion de dependencias y extraccion del usuario autenticado.

Este modulo es donde se ensambla la arquitectura en capas. Cada nivel declara
lo que necesita del inferior y FastAPI construye el grafo completo en cada
peticion:

    router  ->  service  ->  repository  ->  Session (base de datos)

Ninguna capa instancia a la de abajo: la recibe ya construida. Eso mantiene las
dependencias explicitas y permite sustituir cualquier pieza mediante
`app.dependency_overrides` sin tocar el codigo de produccion.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.repositories.user_repository import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.demo_service import DemoService
from app.services.habit_service import HabitService
from app.services.sleep_session_service import SleepSessionService

# Alias para la sesion de base de datos. Usar `Annotated` en lugar de valores
# por defecto con `Depends(...)` mantiene las firmas legibles y compatibles con
# los analizadores estaticos de tipos.
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# NIVEL 1: repositorios (dependen de la sesion de base de datos)
# ---------------------------------------------------------------------------

def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_sleep_session_repository(db: DbSession) -> SleepSessionRepository:
    return SleepSessionRepository(db)


def get_daily_habit_repository(db: DbSession) -> DailyHabitRepository:
    return DailyHabitRepository(db)


def get_sleep_score_repository(db: DbSession) -> SleepScoreRepository:
    return SleepScoreRepository(db)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
SessionRepo = Annotated[SleepSessionRepository, Depends(get_sleep_session_repository)]
HabitRepo = Annotated[DailyHabitRepository, Depends(get_daily_habit_repository)]
ScoreRepo = Annotated[SleepScoreRepository, Depends(get_sleep_score_repository)]


# ---------------------------------------------------------------------------
# NIVEL 2: servicios (dependen de repositorios)
# ---------------------------------------------------------------------------

def get_auth_service(user_repository: UserRepo) -> AuthService:
    return AuthService(user_repository)


def get_sleep_session_service(
    session_repository: SessionRepo,
    habit_repository: HabitRepo,
    score_repository: ScoreRepo,
) -> SleepSessionService:
    """Ensambla el servicio de sesiones.

    Los tres repositorios comparten la MISMA `Session` de SQLAlchemy, porque
    `get_db` esta cacheada por peticion (comportamiento por defecto de
    `Depends`). Esa es la razon de que un unico `commit()` en el servicio
    confirme de forma atomica la sesion de sueno y su score.
    """
    return SleepSessionService(
        session_repository=session_repository,
        habit_repository=habit_repository,
        score_repository=score_repository,
    )


def get_habit_service(
    habit_repository: HabitRepo,
    session_repository: SessionRepo,
    score_repository: ScoreRepo,
) -> HabitService:
    return HabitService(
        habit_repository=habit_repository,
        session_repository=session_repository,
        score_repository=score_repository,
    )


def get_demo_service(
    user_repository: UserRepo,
    session_repository: SessionRepo,
    habit_repository: HabitRepo,
    score_repository: ScoreRepo,
    settings: AppSettings,
) -> DemoService:
    """Ensambla el servicio de cuentas de demostracion.

    Es el unico servicio que recibe la configuracion completa, porque su
    comportamiento depende directamente de ella: vigencia de las cuentas, tope
    de cuentas vivas y dias de historial a generar.
    """
    return DemoService(
        user_repository=user_repository,
        session_repository=session_repository,
        habit_repository=habit_repository,
        score_repository=score_repository,
        settings=settings,
    )


def get_analytics_service(
    session_repository: SessionRepo,
    habit_repository: HabitRepo,
    session_service: Annotated[SleepSessionService, Depends(get_sleep_session_service)],
) -> AnalyticsService:
    """Ensambla el servicio de analitica.

    Recibe `SleepSessionService` ademas de los repositorios: el recalculo de un
    score ya esta implementado alli y se reutiliza en lugar de duplicarlo.
    """
    return AnalyticsService(
        session_repository=session_repository,
        habit_repository=habit_repository,
        session_service=session_service,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SessionServiceDep = Annotated[SleepSessionService, Depends(get_sleep_session_service)]
HabitServiceDep = Annotated[HabitService, Depends(get_habit_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
DemoServiceDep = Annotated[DemoService, Depends(get_demo_service)]


# ---------------------------------------------------------------------------
# NIVEL 3: usuario autenticado
# ---------------------------------------------------------------------------

def _extract_token(
    cookie_token: str | None,
    authorization_header: str | None,
) -> str | None:
    """Obtiene el JWT de la peticion.

    Se aceptan dos transportes, por orden de prioridad:

      1. La cookie httpOnly. Es el mecanismo que usa el frontend: el navegador
         la adjunta solo, y al ser httpOnly el JavaScript de la pagina no puede
         leerla, lo que neutraliza el robo de token mediante XSS.

      2. La cabecera `Authorization: Bearer <token>`. Existe para poder usar la
         API desde herramientas sin navegador (curl, la interfaz /docs, tests
         de integracion). No debilita el modelo de seguridad: una cabecera hay
         que anadirla de forma explicita, asi que no participa de los ataques
         de tipo CSRF, que se apoyan justamente en el envio automatico de
         cookies por parte del navegador.
    """
    if cookie_token:
        return cookie_token

    if authorization_header:
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()

    return None


def get_current_user(
    request: Request,
    user_repository: UserRepo,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Dependencia que resuelve el usuario autenticado de la peticion.

    Cualquier endpoint que la declare queda automaticamente protegido: si el
    token falta, esta expirado o el usuario ya no existe, FastAPI corta la
    peticion con un 401 antes de ejecutar el cuerpo del endpoint.

    La cookie se lee de `request.cookies` y no como parametro `Cookie()` porque
    su nombre es configurable (`COOKIE_NAME`): un parametro con nombre fijo
    dejaria de encontrarla en cuanto se cambiara esa variable de entorno.

    Raises:
        HTTPException 401: token ausente, invalido, expirado, o usuario
            inexistente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado.",
        # Cabecera exigida por el estandar HTTP para las respuestas 401.
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _extract_token(request.cookies.get(settings.COOKIE_NAME), authorization)
    if token is None:
        raise credentials_exception

    user_id = decode_access_token(token)
    if user_id is None:
        # Firma invalida, token expirado o malformado. No se distinguen los
        # casos en la respuesta para no dar pistas a quien sondea la API.
        raise credentials_exception

    user = user_repository.get_by_id(user_id)
    if user is None:
        # El token es criptograficamente valido pero el usuario ya no existe
        # (cuenta eliminada). El token queda invalidado de facto.
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
