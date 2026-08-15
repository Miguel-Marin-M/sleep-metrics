"""Acceso a datos de la tabla `users`."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Encapsula todas las consultas SQL sobre usuarios.

    Recibe la `Session` por constructor en lugar de crearla: eso mantiene el
    control de la transaccion en la capa superior (services) y permite que
    varios repositories participen de la misma unidad de trabajo.

    Los metodos hacen `flush` pero nunca `commit`: quien decide cuando se cierra
    la transaccion es el servicio, porque solo el conoce donde empieza y acaba
    una operacion de negocio.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """Busca un usuario por su clave primaria."""
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por email.

        El email se normaliza a minusculas antes de consultar, en coherencia
        con como se persiste. Asi "Ana@Mail.com" y "ana@mail.com" resuelven a
        la misma cuenta y el indice UNIQUE sigue siendo utilizable (una
        comparacion con lower() sobre la columna impediria usarlo).
        """
        statement = select(User).where(User.email == email.strip().lower())
        return self.db.execute(statement).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        """Comprueba si un email ya tiene cuenta.

        Selecciona solo la columna id en lugar de la entidad completa: no hace
        falta materializar el objeto ORM para responder a una pregunta binaria.
        """
        statement = select(User.id).where(User.email == email.strip().lower()).limit(1)
        return self.db.execute(statement).scalar_one_or_none() is not None

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        is_demo: bool = False,
    ) -> User:
        """Inserta un nuevo usuario.

        El `flush` envia el INSERT a la base de datos dentro de la transaccion
        abierta, lo que hace que PostgreSQL asigne el ID de la secuencia y
        SQLAlchemy lo recupere. Sin el, `user.id` seria None hasta el commit.
        """
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            is_demo=is_demo,
        )
        self.db.add(user)
        self.db.flush()
        return user

    # -----------------------------------------------------------------------
    # Mantenimiento de las cuentas de demostracion
    # -----------------------------------------------------------------------

    def count_demo_users(self) -> int:
        """Numero de cuentas de demostracion vivas."""
        statement = select(func.count(User.id)).where(User.is_demo.is_(True))
        return self.db.execute(statement).scalar_one()

    def delete_demo_users_created_before(self, cutoff: datetime) -> int:
        """Elimina las cuentas de demostracion anteriores a `cutoff`.

        Args:
            cutoff: instante limite. Se borran las creadas ANTES de el.

        Returns:
            Numero de cuentas eliminadas.

        Se emite un DELETE masivo sin cargar las entidades en memoria. Sus
        sesiones, habitos y scores desaparecen por el ON DELETE CASCADE
        declarado en las llaves foraneas, no por la cascada del ORM: esta
        ultima requeriria cargar cada objeto y sus colecciones, convirtiendo una
        sola sentencia en cientos de consultas.
        """
        statement = delete(User).where(
            User.is_demo.is_(True),
            User.created_at < cutoff,
        )
        return self.db.execute(statement).rowcount

    def delete_oldest_demo_users(self, keep_newest: int) -> int:
        """Conserva solo las `keep_newest` cuentas de demostracion mas recientes.

        Es el control de tope que impide que un cliente automatizado llamando al
        endpoint de demostracion en bucle llene la base de datos del plan
        gratuito.

        Returns:
            Numero de cuentas eliminadas.

        Se resuelve en dos pasos (SELECT de ids y despues DELETE) en lugar de un
        DELETE con subconsulta: PostgreSQL no admite LIMIT ni OFFSET dentro del
        DELETE, y esta forma es ademas la que deja explicito que se esta
        borrando por antiguedad.
        """
        stale_ids = (
            select(User.id)
            .where(User.is_demo.is_(True))
            .order_by(User.created_at.desc())
            .offset(keep_newest)
        )

        ids = list(self.db.execute(stale_ids).scalars().all())
        if not ids:
            return 0

        self.db.execute(delete(User).where(User.id.in_(ids)))
        return len(ids)
