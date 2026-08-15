"""Logica de negocio de la autenticacion."""

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    """Orquesta registro y login.

    Recibe el repositorio por constructor (inyeccion de dependencias): el
    servicio depende de una abstraccion de acceso a datos, no de SQLAlchemy.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def register(self, name: str, email: str, password: str) -> User:
        """Crea una cuenta nueva.

        Raises:
            ConflictError: si el email ya tiene cuenta.
        """
        normalized_email = email.strip().lower()

        # Comprobacion previa para poder devolver un 409 con un mensaje util.
        # La garantia real de unicidad sigue siendo la restriccion UNIQUE de la
        # base de datos, que cubre la condicion de carrera entre dos registros
        # simultaneos con el mismo email (ver el manejador de IntegrityError en
        # main.py, que la traduce al mismo 409).
        if self.user_repository.email_exists(normalized_email):
            raise ConflictError("Ya existe una cuenta registrada con ese email.")

        user = self.user_repository.create(
            name=name,
            email=normalized_email,
            # La contrasena en claro muere aqui: a partir de este punto solo
            # existe su hash bcrypt.
            password_hash=hash_password(password),
        )

        # El commit lo hace el servicio, no el repositorio: el limite de la
        # transaccion coincide con el de la operacion de negocio.
        self.user_repository.db.commit()
        return user

    def authenticate(self, email: str, password: str) -> User:
        """Valida credenciales y devuelve el usuario.

        Raises:
            AuthenticationError: si el email no existe o la contrasena no
                coincide.
        """
        user = self.user_repository.get_by_email(email)

        if user is None:
            # Se ejecuta igualmente una verificacion contra un hash ficticio
            # para que el tiempo de respuesta de "email inexistente" y
            # "contrasena incorrecta" sea comparable. Sin esto, un atacante
            # podria enumerar que emails tienen cuenta midiendo la latencia:
            # el caso sin usuario retornaria de inmediato, sin pagar el coste
            # deliberadamente lento de bcrypt.
            verify_password(
                password,
                "$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRS",
            )
            raise AuthenticationError("Email o contrasena incorrectos.")

        if not verify_password(password, user.password_hash):
            # Mensaje deliberadamente identico al anterior: distinguirlos
            # revelaria que emails estan registrados.
            raise AuthenticationError("Email o contrasena incorrectos.")

        return user

    @staticmethod
    def issue_access_token(user: User) -> str:
        """Emite el JWT de sesion para un usuario ya autenticado.

        Se separa de `authenticate` porque son responsabilidades distintas:
        verificar identidad y emitir una credencial de sesion. El router lo
        usa para colocar el token en la cookie httpOnly.
        """
        return create_access_token(subject=user.id)
