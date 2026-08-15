"""Elimina las cuentas de demostracion caducadas.

    python -m scripts.purge_demo_accounts

Se ejecuta automaticamente en cada despliegue desde `start.sh`, justo despues
de aplicar las migraciones.

POR QUE EXISTE, SI LA PURGA YA OCURRE AL CREAR CADA CUENTA
----------------------------------------------------------
El endpoint POST /auth/demo limpia las cuentas caducadas antes de crear una
nueva, lo que cubre el caso normal. Pero esa limpieza solo se dispara si ALGUIEN
visita la demostracion: si el portafolio pasa un mes sin visitas, las ultimas
cuentas creadas se quedarian indefinidamente ocupando espacio en el plan
gratuito de Supabase.

Ejecutarlo en el despliegue garantiza un suelo minimo de mantenimiento sin
depender de una tarea programada, que el plan gratuito de Render no ofrece.

El script no falla nunca de forma que aborte el arranque: un error de limpieza
no es motivo para dejar la API caida, asi que se registra y se sale con codigo 0.
"""

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.repositories.user_repository import UserRepository
from app.services.demo_service import DemoService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sleepmetrics.purge_demo")


def main() -> int:
    """Punto de entrada. Devuelve siempre 0 para no abortar el despliegue."""
    if not settings.DEMO_ACCOUNT_ENABLED:
        logger.info("Cuentas de demostracion desactivadas: no hay nada que purgar.")
        return 0

    # La sesion se construye a mano en lugar de recibirla por inyeccion: aqui no
    # hay peticion HTTP, asi que no existe el ciclo de vida de `get_db`.
    db = SessionLocal()

    try:
        demo_service = DemoService(
            user_repository=UserRepository(db),
            session_repository=SleepSessionRepository(db),
            habit_repository=DailyHabitRepository(db),
            score_repository=SleepScoreRepository(db),
            settings=settings,
        )

        deleted = demo_service.purge_expired_accounts()

        # `purge_expired_accounts` no confirma la transaccion a proposito, para
        # poder componerse con otras operaciones. Aqui es el script quien cierra
        # el limite transaccional.
        db.commit()

        if deleted:
            logger.info(
                "Eliminadas %d cuenta(s) de demostracion con mas de %d horas.",
                deleted,
                settings.DEMO_ACCOUNT_TTL_HOURS,
            )
        else:
            logger.info("No habia cuentas de demostracion caducadas.")

    except SQLAlchemyError as exc:
        db.rollback()
        # Se registra pero no se propaga: un fallo de mantenimiento no debe
        # impedir que la API arranque y atienda a los usuarios reales.
        logger.error("No se pudo purgar las cuentas de demostracion: %s", exc)

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
