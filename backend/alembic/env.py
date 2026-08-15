"""Entorno de ejecucion de Alembic para SleepMetrics.

Este archivo es el puente entre Alembic y la aplicacion. Hace tres cosas:

  1. Inyecta la URL de conexion desde la configuracion de la app, en lugar de
     leerla de alembic.ini (donde quedaria versionada en git junto con la
     contrasena de la base de datos).
  2. Expone `Base.metadata` como `target_metadata`, que es lo que permite a
     `alembic revision --autogenerate` comparar los modelos con el estado real
     de la base de datos.
  3. Define las opciones de comparacion del autogenerado.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# La importacion de `app` funciona gracias a `prepend_sys_path = .` en
# alembic.ini, que anade la carpeta backend/ al sys.path.
from app.core.config import settings

# Importar el paquete de modelos ejecuta el __init__.py, que a su vez importa
# TODOS los modelos y los registra en Base.metadata. Si un modelo no llegara a
# importarse, el autogenerado no lo veria y llegaria a proponer un DROP TABLE
# de su tabla por considerarla sobrante.
from app.models import Base

# Objeto de configuracion de Alembic, con acceso a los valores de alembic.ini.
config = context.config

# Inyeccion de la URL real de conexion en tiempo de ejecucion.
#
# `set_main_option` escapa el simbolo '%' porque ConfigParser lo interpreta
# como marcador de interpolacion. Es un detalle que importa de verdad: las
# contrasenas codificadas en percent-encoding (por ejemplo `p%40ss`) romperian
# la carga de la configuracion sin este escape.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Configuracion del logging declarada en alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo del autogenerado.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL de las migraciones sin conectarse a la base de datos.

    Se invoca con `alembic upgrade head --sql`. Es util para revisar en una
    pull request exactamente que DDL se va a ejecutar, o para entregar el
    script a un administrador de base de datos que lo aplique a mano.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones conectandose a la base de datos.

    Es el modo que usan `alembic upgrade head` y, por tanto, el arranque
    automatico del backend en Render (ver start.sh).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: el proceso de migracion es efimero y abre una unica
        # conexion. Mantener un pool abierto no aporta nada y consumiria cupo
        # de conexiones del free tier de Supabase durante el despliegue.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # compare_type detecta cambios de tipo de columna (por ejemplo,
            # VARCHAR(120) -> VARCHAR(200)). Sin el, Alembic los ignora.
            compare_type=True,
            # compare_server_default detecta cambios en los valores DEFAULT.
            compare_server_default=True,
            # Envuelve cada migracion en su propia transaccion. PostgreSQL
            # soporta DDL transaccional, asi que una migracion que falle a la
            # mitad revierte por completo en lugar de dejar el schema roto.
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
