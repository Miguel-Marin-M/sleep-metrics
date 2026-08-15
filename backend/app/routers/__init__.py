"""Capa de routers: la frontera HTTP de la aplicacion.

Responsabilidades de esta capa, y solo estas:
  - Declarar rutas, metodos y codigos de estado.
  - Validar la entrada (delegando en los schemas Pydantic).
  - Declarar las dependencias que necesita (usuario autenticado, servicios).
  - Devolver el schema de respuesta.

Lo que esta capa NO hace:
  - Acceder a la base de datos. Ningun router importa SQLAlchemy ni recibe una
    `Session`; siempre pasa por services -> repositories.
  - Contener reglas de negocio. Si un endpoint necesita decidir algo sobre el
    dominio, esa decision pertenece a un servicio.
"""

from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.habits import router as habits_router
from app.routers.sessions import router as sessions_router

__all__ = ["auth_router", "sessions_router", "habits_router", "analytics_router"]
