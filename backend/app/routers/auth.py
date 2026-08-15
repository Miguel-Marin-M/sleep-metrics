"""Endpoints de autenticacion.

El JWT nunca aparece en el cuerpo de las respuestas: viaja exclusivamente en
una cookie httpOnly que emite el backend. Consecuencia directa de esa decision
es que el frontend no puede inspeccionar la sesion por su cuenta, y de ahi el
endpoint GET /auth/me.
"""

from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import Settings
from app.core.dependencies import AppSettings, AuthServiceDep, CurrentUser, DemoServiceDep
from app.schemas.auth import AuthResponse, LoginRequest, MessageResponse, RegisterRequest
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


def _set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    """Coloca el JWT en la cookie de sesion.

    Parametros de seguridad de la cookie:

      httponly=True
        El JavaScript de la pagina no puede leerla. Es la proteccion central
        de este diseno: aunque se cuele un XSS en el frontend, el token no es
        exfiltrable.

      secure
        La cookie solo viaja por HTTPS. Obligatorio en produccion, y ademas
        requisito tecnico de SameSite=None.

      samesite
        En produccion vale "none" porque frontend (Vercel) y backend (Render)
        estan en dominios distintos y la peticion es cross-site; sin ese valor
        el navegador simplemente no enviaria la cookie. En desarrollo vale
        "lax", que es mas restrictivo y suficiente porque ambos corren en
        localhost.

    Nota sobre CSRF: SameSite=None reabre en teoria la puerta a peticiones
    cross-site con cookie automatica. Aqui esta mitigado porque todos los
    endpoints que modifican estado consumen `application/json`, un Content-Type
    que obliga al navegador a lanzar un preflight OPTIONS; ese preflight lo
    rechaza CORS para cualquier origen que no este en CORS_ORIGINS. Un
    formulario HTML malicioso no puede emitir ese Content-Type, de modo que no
    llega a ejecutarse la peticion real.
    """
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta nueva",
)
def register(
    payload: RegisterRequest,
    response: Response,
    auth_service: AuthServiceDep,
    settings: AppSettings,
) -> AuthResponse:
    """Crea una cuenta y deja al usuario autenticado.

    Se emite la cookie de sesion en el propio registro para evitar obligar al
    usuario a iniciar sesion inmediatamente despues de crear la cuenta.
    """
    user = auth_service.register(
        name=payload.name,
        email=payload.email,
        password=payload.password,
    )

    token = auth_service.issue_access_token(user)
    _set_auth_cookie(response, token, settings)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Cuenta creada correctamente.",
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Iniciar sesion",
)
def login(
    payload: LoginRequest,
    response: Response,
    auth_service: AuthServiceDep,
    settings: AppSettings,
) -> AuthResponse:
    """Valida credenciales y emite la cookie de sesion."""
    user = auth_service.authenticate(email=payload.email, password=payload.password)

    token = auth_service.issue_access_token(user)
    _set_auth_cookie(response, token, settings)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Sesion iniciada correctamente.",
    )


@router.post(
    "/demo",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta de demostracion y entrar",
)
def start_demo(
    response: Response,
    demo_service: DemoServiceDep,
    auth_service: AuthServiceDep,
    settings: AppSettings,
) -> AuthResponse:
    """Crea una cuenta de demostracion aislada, la siembra y abre sesion.

    Permite probar la aplicacion completa sin registrarse, que es el requisito
    de una demostracion de portafolio.

    POR QUE UNA CUENTA POR VISITANTE Y NO UNA COMPARTIDA
    ---------------------------------------------------
    Con una unica cuenta de demostracion publica, todos los visitantes escriben
    sobre los mismos datos: el primero que borra el historial deja la
    aplicacion vacia para los siguientes, y dos personas simultaneas se pisan
    los cambios en tiempo real. Dando una cuenta desechable a cada uno, la
    aplicacion funciona al 100 % (crear, editar y borrar de verdad, sin
    simulaciones ni restricciones) y nadie puede estropearle la prueba a nadie.

    Las cuentas se limpian solas: cada llamada elimina primero las caducadas y
    aplica el tope de cuentas vivas, asi que el sistema se mantiene sin
    depender de ninguna tarea programada.

    Raises:
        HTTPException 404: si la demostracion esta desactivada por
            configuracion. Se responde 404 y no 403 para no anunciar la
            existencia de un endpoint deshabilitado.
    """
    if not settings.DEMO_ACCOUNT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta de demostracion no esta disponible.",
        )

    user = demo_service.create_demo_account()

    token = auth_service.issue_access_token(user)
    _set_auth_cookie(response, token, settings)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        message="Cuenta de demostracion lista.",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Usuario de la sesion actual",
)
def get_me(current_user: CurrentUser) -> UserResponse:
    """Devuelve el usuario autenticado.

    Este endpoint es imprescindible con autenticacion por cookie httpOnly: el
    frontend no puede leer la cookie ni decodificar el token, asi que la unica
    forma de saber si hay sesion activa (y de quien es) es preguntarselo al
    backend. Es la llamada que el contexto de autenticacion del frontend hace
    al arrancar la aplicacion.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Cerrar sesion",
)
def logout(response: Response, settings: AppSettings) -> MessageResponse:
    """Cierra la sesion borrando la cookie.

    Tambien es necesario con cookies httpOnly: el frontend no puede eliminar
    una cookie que no puede ver, de modo que el borrado debe ordenarlo el
    servidor mediante la cabecera Set-Cookie.

    Los atributos path, domain, secure y samesite deben coincidir exactamente
    con los usados al emitirla; si difieren, el navegador considera que son
    cookies distintas y la original sobrevive.
    """
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
    return MessageResponse(message="Sesion cerrada correctamente.")
