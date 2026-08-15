"""Modelo SQLAlchemy de la tabla `users`."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    # Importaciones solo para el type checker: evitan un ciclo de imports en
    # tiempo de ejecucion (user -> sleep_session -> user).
    from app.models.daily_habit import DailyHabit
    from app.models.sleep_session import SleepSession


class User(Base):
    """Cuenta de usuario de la aplicacion.

    La autenticacion es propia del backend (JWT + bcrypt). Esta tabla no tiene
    ninguna relacion con el esquema `auth` de Supabase: Supabase se usa aqui
    unicamente como PostgreSQL administrado.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        # Identity(always=True) genera GENERATED ALWAYS AS IDENTITY: PostgreSQL
        # rechaza cualquier intento de insertar un ID explicito, lo que impide
        # desincronizar la secuencia por error.
        Identity(always=True),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # unique=True crea implicitamente el indice usado en el login por email.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Hash bcrypt de 60 caracteres. Nunca se expone en ningun schema Pydantic.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Marca las cuentas desechables que genera el endpoint POST /auth/demo.
    #
    # Se modela como columna y no deduciendo el caracter de demostracion del
    # dominio del email: una comparacion de cadenas seria fragil (bastaria que
    # alguien se registrase con ese dominio para colarse en la purga) y ademas
    # impediria indexar la condicion de forma eficiente.
    is_demo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        # El valor por defecto se calcula en el servidor de base de datos, no
        # en Python: asi todas las filas usan el mismo reloj aunque haya varias
        # instancias del backend desplegadas.
        server_default=func.timezone("utc", func.now()),
    )

    # -- Relaciones ---------------------------------------------------------
    # cascade="all, delete-orphan" replica en el ORM el ON DELETE CASCADE de la
    # base de datos, para que borrar un User desde Python tambien limpie su
    # historial sin dejar filas huerfanas.
    #
    # lazy="select" (el valor por defecto) es intencional: estas colecciones no
    # se cargan hasta que alguien las recorre. Importa porque la dependencia de
    # autenticacion carga el User en CADA peticion protegida, y una estrategia
    # eager traeria de vuelta todo el historial del usuario cada vez sin que
    # ningun endpoint lo necesite. El acceso al historial va siempre por
    # SleepSessionRepository, con su propia paginacion.
    sleep_sessions: Mapped[list["SleepSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    daily_habits: Mapped[list["DailyHabit"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # El backend normaliza el email a minusculas antes de guardarlo. Este
        # CHECK protege la invariante aunque en el futuro se escriba en la
        # tabla desde otro sitio (una migracion de datos, un script manual).
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        # Indice PARCIAL: solo cubre las filas con is_demo = true.
        #
        # Es la forma correcta de indexar una columna booleana muy sesgada. Las
        # cuentas reales seran la inmensa mayoria de la tabla y jamas se
        # consultan por esta columna; un indice completo las incluiria todas,
        # ocupando espacio y encareciendo cada INSERT sin beneficio. El indice
        # parcial solo contiene las cuentas de demostracion, que es exactamente
        # el conjunto que recorren la purga y el control de tope.
        Index(
            "ix_users_is_demo",
            "is_demo",
            postgresql_where=text("is_demo"),
        ),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
