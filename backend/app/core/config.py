"""Configuracion de la aplicacion leida desde variables de entorno.

Se usa `pydantic-settings`, que valida y castea los valores del entorno con las
mismas reglas que cualquier modelo Pydantic. La ventaja frente a leer
`os.environ` a mano es que un valor ausente o mal tipado revienta en el
arranque con un mensaje claro, en lugar de provocar un TypeError oscuro en la
primera peticion.

El objeto `settings` se construye una unica vez (ver `get_settings`) y se
importa desde el resto de la aplicacion.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contrato tipado de todas las variables de entorno que la app necesita."""

    model_config = SettingsConfigDict(
        # Carga automatica del archivo .env de la carpeta backend/ en desarrollo.
        # En Render no existe .env: las variables llegan ya inyectadas en el
        # entorno del proceso, y pydantic-settings les da prioridad.
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Ignora variables del entorno que no esten declaradas aqui (Render
        # inyecta decenas de variables propias como RENDER_SERVICE_ID).
        extra="ignore",
    )

    # -- Entorno ------------------------------------------------------------
    ENVIRONMENT: Literal["development", "production"] = "development"

    # -- Base de datos ------------------------------------------------------
    # Sin valor por defecto a proposito: si falta, la app no debe arrancar.
    DATABASE_URL: str

    # -- JWT ----------------------------------------------------------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, gt=0)  # 7 dias

    # -- Cookie de sesion ---------------------------------------------------
    COOKIE_NAME: str = "sleepmetrics_access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    # Cadena vacia se normaliza a None (ver validador mas abajo): dejar que el
    # navegador asocie la cookie al host emisor es el comportamiento correcto
    # cuando backend y frontend viven en dominios distintos.
    COOKIE_DOMAIN: str | None = None

    # -- CORS ---------------------------------------------------------------
    # Se recibe como cadena separada por comas porque las variables de entorno
    # solo pueden ser texto. Se expone parseada en `cors_origins`.
    CORS_ORIGINS: str = "http://localhost:3000"

    # -- Cuentas de demostracion -------------------------------------------
    # Cada visitante que pulsa "Probar la aplicacion" recibe su PROPIA cuenta
    # desechable, ya sembrada con datos ficticios. Aislar por visitante es lo
    # que evita que dos personas se pisen los datos, que es el problema
    # inevitable de una unica cuenta de demostracion compartida.

    # Interruptor general. Permite desactivar la demo sin redesplegar codigo.
    DEMO_ACCOUNT_ENABLED: bool = True

    # Vigencia de una cuenta de demostracion. Pasado este plazo se elimina
    # junto con todos sus datos (por la cascada de las llaves foraneas).
    DEMO_ACCOUNT_TTL_HOURS: int = Field(default=24, gt=0)

    # Tope de cuentas de demostracion vivas simultaneamente. Es la proteccion
    # frente a un bot que llame al endpoint en bucle e infle la base de datos
    # del plan gratuito: al superar el tope se eliminan las mas antiguas.
    DEMO_ACCOUNT_MAX_ACTIVE: int = Field(default=200, gt=0)

    # Dias de historial ficticio que se generan en cada cuenta.
    #
    # 90 dias no es un numero redondo elegido al azar: es el minimo con el que
    # las correlaciones del panel salen estables. Con 45 dias quedaban unas 30
    # muestras utiles, y con esa cantidad el coeficiente de Pearson sobre un
    # predictor discreto como los miligramos de cafeina oscilaba entre -0.60 y
    # +0.07 solo con cambiar la semilla del generador: la calidad de la
    # demostracion dependia de la suerte. A 90 dias el coeficiente se estabiliza
    # y ninguna semilla probada produce un panel pobre.
    DEMO_SEED_DAYS: int = Field(default=90, gt=0, le=365)

    # -- Servidor -----------------------------------------------------------
    PORT: int = 8000

    # ---------------------------------------------------------------------
    # Validadores
    # ---------------------------------------------------------------------

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Fuerza el driver psycopg2 en la URL de conexion.

        Supabase (y Heroku, y otros proveedores) entregan la cadena con el
        prefijo `postgres://` o `postgresql://`. SQLAlchemy 2.x ya no reconoce
        `postgres://`, y sin el sufijo `+psycopg2` elegiria el driver por
        defecto del dialecto. Normalizar aqui evita un fallo de conexion en
        produccion causado solo por copiar y pegar la cadena tal cual.
        """
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg2://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value

    @field_validator("COOKIE_DOMAIN", mode="before")
    @classmethod
    def empty_domain_to_none(cls, value: str | None) -> str | None:
        """Convierte COOKIE_DOMAIN="" en None.

        Una variable de entorno declarada pero vacia llega como cadena vacia,
        y `Set-Cookie: Domain=` es una cabecera invalida. None hace que el
        parametro se omita por completo.
        """
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def secret_must_be_strong(cls, value: str) -> str:
        """Rechaza secretos triviales: firmar HS256 con una clave corta es
        equivalente a no firmar."""
        if len(value) < 32:
            raise ValueError(
                "JWT_SECRET_KEY debe tener al menos 32 caracteres. "
                'Genera uno con: python -c "import secrets; '
                'print(secrets.token_urlsafe(64))"'
            )
        return value

    # ---------------------------------------------------------------------
    # Propiedades derivadas
    # ---------------------------------------------------------------------

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parseada como lista de origenes exactos.

        No se admite "*": el middleware de CORS con `allow_credentials=True`
        (necesario para enviar la cookie de sesion) exige origenes explicitos,
        segun la especificacion de CORS.
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia unica de configuracion.

    `lru_cache` la convierte en un singleton perezoso: el .env se lee una sola
    vez por proceso. Ademas, al ser una funcion, puede inyectarse con
    `Depends(get_settings)` y sustituirse en tests mediante
    `app.dependency_overrides`.
    """
    return Settings()


# Instancia global para importacion directa desde modulos que no forman parte
# del grafo de dependencias de FastAPI (por ejemplo, el env.py de Alembic).
settings = get_settings()
