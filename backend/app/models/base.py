"""Clase base declarativa compartida por todos los modelos SQLAlchemy.

Todos los modelos heredan de `Base`, de modo que `Base.metadata` acaba
conteniendo la definicion completa del schema. Ese objeto `metadata` es
exactamente lo que Alembic compara contra la base de datos real para
autogenerar migraciones.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convencion de nombres explicita para indices y restricciones.
#
# Sin ella, PostgreSQL genera nombres automaticos para las constraints y
# Alembic no puede emitir un DROP CONSTRAINT fiable en un downgrade (no sabe
# como se llama la restriccion que debe eliminar). Fijar la convencion hace que
# las migraciones sean reversibles de forma determinista.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",   # indices
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",   # unique
    "ck": "ck_%(table_name)s_%(constraint_name)s",   # check
    "fk": "fk_%(table_name)s_%(column_0_name)s",     # foreign key
    "pk": "pk_%(table_name)s",                       # primary key
}


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy 2.0 para todos los modelos."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
