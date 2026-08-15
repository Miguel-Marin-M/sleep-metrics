"""Motor de SQLAlchemy, fabrica de sesiones y dependencia de sesion por request.

Esta es la unica pieza del proyecto que sabe COMO se abre una conexion. Los
repositories reciben una `Session` ya construida; nunca la crean por su cuenta.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Motor de conexion
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping emite un "SELECT 1" barato antes de entregar una conexion
    # del pool. Es imprescindible en este despliegue: el free tier de Render
    # duerme el servicio tras 15 minutos de inactividad y el pooler de Supabase
    # cierra conexiones ociosas, de modo que sin esto la primera peticion tras
    # un periodo inactivo fallaria con "server closed the connection".
    pool_pre_ping=True,
    # Recicla conexiones cada 5 minutos, por debajo del tiempo de corte del
    # pooler de Supabase.
    pool_recycle=300,
    # Pool deliberadamente pequeno: el free tier de Supabase limita el numero
    # total de conexiones concurrentes, y una sola instancia de Render no
    # necesita mas.
    pool_size=5,
    max_overflow=5,
    # Registra cada sentencia SQL emitida cuando se trabaja en local. En
    # produccion se silencia para no inundar los logs ni filtrar datos.
    echo=not settings.is_production,
    future=True,
)

# ---------------------------------------------------------------------------
# Fabrica de sesiones
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    # autoflush=False evita que SQLAlchemy escriba en la base de datos de forma
    # implicita antes de cada consulta. El control de cuando se persiste queda
    # asi en manos de la capa de servicios, que es donde vive la transaccion.
    autoflush=False,
    autocommit=False,
    # expire_on_commit=False mantiene los atributos de los objetos accesibles
    # despues del commit. Sin esto, serializar un modelo recien creado en la
    # respuesta HTTP dispararia una recarga desde la base de datos (o un
    # DetachedInstanceError si la sesion ya se cerro).
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que provee una sesion por peticion HTTP.

    Ciclo de vida:
      1. Se abre una sesion al comenzar la peticion.
      2. Se cede al endpoint (y, a traves de el, a services y repositories).
      3. Si el endpoint lanza una excepcion se hace rollback, de forma que
         nunca queden cambios a medias en la transaccion.
      4. La sesion se cierra siempre y la conexion vuelve al pool.

    El commit NO se hace aqui: es responsabilidad de la capa de servicios, que
    es la unica que conoce los limites de una operacion de negocio.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
