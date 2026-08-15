"""Creacion y siembra de las cuentas de demostracion.

PROBLEMA QUE RESUELVE
---------------------
Un portafolio necesita que cualquiera pueda probar la aplicacion sin
registrarse. La solucion habitual (una unica cuenta de demostracion con
credenciales publicas) tiene un fallo que no se puede tapar: todos los
visitantes comparten los mismos datos. Basta con que uno borre el historial
para que el siguiente encuentre la aplicacion vacia, y si dos personas entran a
la vez se pisan los cambios mutuamente en tiempo real.

Aqui cada visitante recibe su PROPIA cuenta desechable, ya sembrada. Nadie
puede estropearle la demostracion a nadie, y la aplicacion funciona al 100 %:
se puede crear, editar y borrar sin restricciones ni simulaciones.

El coste de ese aislamiento son cuentas acumuladas, que se controla por dos
vias complementarias:

  - CADUCIDAD: se eliminan las anteriores a DEMO_ACCOUNT_TTL_HOURS.
  - TOPE: nunca hay mas de DEMO_ACCOUNT_MAX_ACTIVE vivas a la vez.

Ambas se ejecutan antes de crear cada cuenta nueva, de modo que el sistema se
mantiene solo sin depender de ninguna tarea programada externa.

FORMA DE LOS DATOS GENERADOS
----------------------------
No son numeros al azar: estan construidos para que la analitica tenga algo real
que mostrar. Un historial aleatorio uniforme produciria correlaciones nulas y un
"mejor dia de la semana" sin sentido, que es justo la parte del proyecto que
merece la pena ensenar.

  - Noches de viernes y sabado: se acuesta mas tarde, mas tiempo de pantalla y
    mas interrupciones. Hace que el mejor y el peor dia de la semana difieran
    de forma clara.
  - Cafeina independiente del dia de la semana, y con la hora del ultimo
    consumo tanto mas tardia cuanta mas cantidad. Eso produce una correlacion
    negativa clara con el score, sin que el efecto del fin de semana la
    contamine.
  - Algunos dias sin registro de habitos y algunas noches sin registrar, porque
    nadie anota absolutamente todos los dias. De paso, esos huecos ejercitan el
    camino de "score parcial" (habits_available = false).
"""

import secrets
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from random import Random

from app.core.config import Settings
from app.core.security import hash_password
from app.models.daily_habit import DailyHabit
from app.models.sleep_session import SleepSession
from app.models.user import User
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_score_repository import SleepScoreRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.repositories.user_repository import UserRepository
from app.services.night import night_date
from app.services.scoring_service import calculate_sleep_score

# Subdominio usado en el email de las cuentas desechables.
#
# La direccion NUNCA se usa para enviar correo: es solo un identificador unico
# que satisface la restriccion UNIQUE de la columna `email`.
#
# No se emplean los dominios de uso especial reservados (.local, .invalid,
# .test, .example) aunque conceptualmente encajarian mejor: `email-validator`,
# la libreria que respalda a `EmailStr` de Pydantic, los rechaza explicitamente,
# y el schema de respuesta no podria serializar al usuario recien creado.
#
# Que un email real pudiera coincidir con este patron es irrelevante: la
# condicion de cuenta de demostracion la marca la columna `is_demo`, no el
# dominio del email. Ese es justamente el motivo de haberla modelado como
# columna.
DEMO_EMAIL_DOMAIN = "demo.sleepmetrics.app"

DEMO_USER_NAME = "Invitado"

# Semilla fija del generador aleatorio.
#
# Hace que todas las cuentas de demostracion contengan exactamente el mismo
# historial. Es deliberado: asi se sabe con certeza que aspecto tiene la demo
# que vera un reclutador, en vez de depender de que una tirada desafortunada
# produzca un panel poco interesante. Las FECHAS si son relativas al momento de
# creacion, de modo que las ventanas de 7 y 30 dias siempre tienen datos.
DEMO_RANDOM_SEED = 20260815

# Probabilidad de que una noche no se registre.
SKIP_NIGHT_PROBABILITY = 0.11

# Probabilidad de que un dia registrado no tenga habitos anotados.
SKIP_HABITS_PROBABILITY = 0.15

# Notas de ejemplo. Se reparten de forma dispersa: llenar todas las filas de
# texto haria la tabla ilegible y no aportaria realismo.
def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Acota un valor al intervalo [minimum, maximum]."""
    return max(minimum, min(maximum, value))


DEMO_NOTES = [
    "Cena tardia y pesada.",
    "Ruido en la calle durante la madrugada.",
    "Habitacion demasiado calurosa.",
    "Me acoste nada mas terminar de entrenar.",
    "Dia de mucho estres en el trabajo.",
    "Desperte descansado, sin despertador.",
    "Lei un rato en papel antes de dormir.",
]


@dataclass(frozen=True)
class _NightPlan:
    """Plan de una noche antes de convertirla en filas de base de datos."""

    habit_date: date_type
    sleep_start: datetime
    sleep_end: datetime
    interruptions: int
    notes: str | None
    # None cuando ese dia no tiene habitos registrados.
    caffeine_mg: int | None
    last_caffeine_time: time | None
    exercise_minutes: int | None
    screen_minutes: int | None


class DemoService:
    """Crea cuentas de demostracion aisladas y las siembra con datos ficticios."""

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SleepSessionRepository,
        habit_repository: DailyHabitRepository,
        score_repository: SleepScoreRepository,
        settings: Settings,
    ) -> None:
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.habit_repository = habit_repository
        self.score_repository = score_repository
        self.settings = settings

    # -----------------------------------------------------------------------
    # Caso de uso principal
    # -----------------------------------------------------------------------

    def create_demo_account(self) -> User:
        """Crea una cuenta de demostracion nueva, ya sembrada.

        Returns:
            El usuario recien creado, listo para recibir una cookie de sesion.
        """
        # El mantenimiento se ejecuta ANTES de crear la cuenta nueva. Aprovechar
        # esta llamada evita depender de una tarea programada externa, que en el
        # plan gratuito de Render no existe.
        self.purge_expired_accounts()
        self._enforce_active_limit()

        user = self._create_user()
        self._seed_history(user)

        # Un unico commit para el alta y todo su historial: o el visitante
        # recibe una cuenta completa, o no recibe ninguna.
        self.user_repository.db.commit()

        return user

    def purge_expired_accounts(self) -> int:
        """Elimina las cuentas de demostracion que han superado su vigencia.

        Returns:
            Numero de cuentas eliminadas.

        No hace commit: lo cierra quien la llama. Asi puede formar parte de la
        misma transaccion que la creacion de una cuenta nueva, o ejecutarse por
        separado desde el script de mantenimiento del despliegue.
        """
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            hours=self.settings.DEMO_ACCOUNT_TTL_HOURS
        )
        return self.user_repository.delete_demo_users_created_before(cutoff)

    # -----------------------------------------------------------------------
    # Helpers internos
    # -----------------------------------------------------------------------

    def _enforce_active_limit(self) -> None:
        """Aplica el tope de cuentas de demostracion vivas.

        Sin este control, un cliente automatizado llamando al endpoint en bucle
        podria llenar la base de datos del plan gratuito. Se eliminan siempre
        las mas antiguas, que son las que menos probablemente esten en uso.
        """
        if self.user_repository.count_demo_users() < self.settings.DEMO_ACCOUNT_MAX_ACTIVE:
            return

        # Se deja hueco para la cuenta que esta a punto de crearse.
        self.user_repository.delete_oldest_demo_users(
            keep_newest=self.settings.DEMO_ACCOUNT_MAX_ACTIVE - 1
        )

    def _create_user(self) -> User:
        """Da de alta la cuenta desechable.

        El email lleva un sufijo aleatorio para no colisionar con la restriccion
        UNIQUE, y la contrasena es aleatoria y no se comunica a nadie: el acceso
        se concede directamente mediante la cookie de sesion que emite el
        endpoint, nunca a traves del formulario de login.
        """
        suffix = secrets.token_hex(5)

        return self.user_repository.create(
            name=DEMO_USER_NAME,
            email=f"demo-{suffix}@{DEMO_EMAIL_DOMAIN}",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            is_demo=True,
        )

    def _seed_history(self, user: User) -> None:
        """Genera y persiste el historial ficticio de la cuenta.

        La insercion va por lotes (tres idas a la base de datos en total, una
        por tabla) en lugar de fila a fila. Contra una base remota como
        Supabase, insertar ~120 filas de una en una anadiria varios segundos de
        espera justo en la primera pantalla que ve el visitante.
        """
        plans = self._build_night_plans()

        # -- 1. Habitos ------------------------------------------------------
        # Se insertan primero porque el calculo del score los necesita.
        habits_by_date: dict[date_type, DailyHabit] = {}
        habit_rows = [
            DailyHabit(
                user_id=user.id,
                date=plan.habit_date,
                caffeine_mg=plan.caffeine_mg,
                last_caffeine_time=plan.last_caffeine_time,
                exercise_minutes=plan.exercise_minutes,
                screen_time_before_bed_minutes=plan.screen_minutes,
            )
            for plan in plans
            if plan.caffeine_mg is not None
        ]

        for habit in self.habit_repository.create_many(habit_rows):
            habits_by_date[habit.date] = habit

        # -- 2. Sesiones de sueno --------------------------------------------
        session_rows = [
            SleepSession(
                user_id=user.id,
                sleep_start=plan.sleep_start,
                sleep_end=plan.sleep_end,
                interruptions=plan.interruptions,
                notes=plan.notes,
            )
            for plan in plans
        ]
        sessions = self.session_repository.create_many(session_rows)

        # -- 3. Scores -------------------------------------------------------
        # Se calculan con el MISMO servicio de scoring que usa la aplicacion en
        # produccion, no con una formula simplificada para la demo. Es lo que
        # garantiza que los numeros del panel sean coherentes con el desglose
        # que vera el visitante al abrir cualquier sesion.
        scores = [
            (
                session.id,
                calculate_sleep_score(
                    session=session,
                    # Se resuelve por la NOCHE de la sesion, igual que hace la
                    # aplicacion en produccion: las noches generadas con hora de
                    # acostarse posterior a medianoche caen en la fecha del dia
                    # siguiente, pero sus habitos son los de la noche anterior.
                    habit=habits_by_date.get(night_date(session.sleep_start)),
                ).score,
            )
            for session in sessions
        ]
        self.score_repository.create_many(scores)

    def _build_night_plans(self) -> list[_NightPlan]:
        """Construye el plan de todas las noches, de la mas antigua a la mas reciente.

        Toda la aleatoriedad del generador esta confinada en este metodo, que no
        toca la base de datos. Eso permite razonar sobre la forma de los datos
        sin mezclarla con la persistencia.
        """
        rng = Random(DEMO_RANDOM_SEED)
        today = datetime.now().date()

        plans: list[_NightPlan] = []

        # Se recorre de mas antiguo a mas reciente. Se empieza en
        # DEMO_SEED_DAYS dias atras y se termina AYER: no se genera la noche de
        # hoy porque a media manana el usuario todavia no la habria registrado,
        # y ademas deja al visitante la primera accion natural que probar.
        for days_ago in range(self.settings.DEMO_SEED_DAYS, 0, -1):
            night = today - timedelta(days=days_ago)

            if rng.random() < SKIP_NIGHT_PROBABILITY:
                continue

            # La noche mas reciente no se acuesta despues de medianoche: su
            # sleep_start caeria en el dia de hoy y, si el visitante crea la
            # cuenta de madrugada, la hora de despertar quedaria en el futuro.
            plans.append(self._plan_night(rng, night, allow_after_midnight=days_ago >= 2))

        return plans

    @staticmethod
    def _plan_night(
        rng: Random,
        night: date_type,
        allow_after_midnight: bool,
    ) -> _NightPlan:
        """Genera los valores de una noche concreta.

        Args:
            rng: generador con semilla fija.
            night: fecha que identifica la noche.
            allow_after_midnight: si se permite que la hora de acostarse caiga
                despues de medianoche.

        Una version anterior mantenia todas las horas de acostarse antes de
        medianoche por necesidad: mientras la sesion se emparejaba con la fecha
        cruda de `sleep_start`, una hora posterior la habria desplazado al dia
        siguiente y dos noches consecutivas podrian haber reclamado el mismo
        registro de habitos.

        Con la regla de `app.services.night` esa restriccion desaparece: tanto
        las 23:30 del dia N como las 00:45 del dia N+1 pertenecen a la noche N,
        de modo que ya se pueden generar ambos casos. El historial resulta mas
        realista y, de paso, ejercita la regla.
        """
        # Viernes (4) y sabado (5): noches de fin de semana.
        is_weekend = night.weekday() in (4, 5)

        # =====================================================================
        # PASO 1: los habitos del dia
        #
        # Se deciden ANTES que la noche, porque en el orden causal real son la
        # causa y no la consecuencia: lo que uno hizo durante el dia condiciona
        # como duerme esa noche.
        # =====================================================================
        has_habits = rng.random() >= SKIP_HABITS_PROBABILITY

        caffeine_mg: int | None = None
        last_caffeine_time: time | None = None
        exercise_minutes: int | None = None
        screen_minutes: int | None = None

        if has_habits:
            # La CANTIDAD de cafeina se sortea sin relacion con el dia de la
            # semana, y esa independencia es deliberada.
            #
            # Una primera version daba mas cafeina entre semana, lo que parecia
            # mas realista pero introducia una variable de confusion: entre
            # semana tambien se duerme mejor (menos pantallas, menos
            # interrupciones), de modo que el efecto del dia de la semana
            # tapaba al de la cafeina y la correlacion salia POSITIVA. El panel
            # acababa afirmando "cuanta mas cafeina, mejor descansas", justo el
            # mensaje contrario al que el proyecto quiere demostrar.
            caffeine_mg = rng.choice([0, 95, 130, 190, 250, 320, 380])

            if caffeine_mg > 0:
                # La hora del ultimo consumo se acopla a la CANTIDAD, y de
                # forma monotona: mas miligramos implica una hora mas tardia.
                #
                # Es realista (380 mg no se toman de una sentada por la manana,
                # sino encadenando cafes durante el dia) y es lo que hace que la
                # correlacion del panel funcione. El coeficiente de Pearson
                # relaciona los MILIGRAMOS BRUTOS con el score, mientras que la
                # penalizacion real depende de cantidad POR proximidad: un dia
                # de 380 mg tomados a las 09:00 no penaliza nada y entra en el
                # calculo como ruido puro. Con un acoplamiento debil, ese ruido
                # hacia que el coeficiente oscilara entre -0.56 y -0.07 segun la
                # semilla; con este, la cantidad es un buen indicador de la
                # penalizacion y la relacion se sostiene.
                if caffeine_mg <= 130:
                    # Consumo bajo: el cafe de la manana.
                    caffeine_minutes = rng.randint(7 * 60 + 30, 13 * 60)
                elif caffeine_mg <= 190:
                    # Intermedio: puede estirarse hasta media tarde.
                    caffeine_minutes = rng.randint(11 * 60, 18 * 60)
                else:
                    # Consumo alto: cafes encadenados hasta la tarde-noche.
                    caffeine_minutes = rng.randint(17 * 60, 21 * 60 + 30)

                last_caffeine_time = time(
                    hour=caffeine_minutes // 60,
                    minute=caffeine_minutes % 60,
                )

            # Ejercicio: se registra como seguimiento, no entra en el score.
            exercise_minutes = rng.choice([0, 0, 20, 30, 45, 60, 75])

            # Pantallas antes de dormir: bastante mas en fin de semana.
            screen_minutes = rng.randint(45, 165) if is_weekend else rng.randint(10, 95)

        # =====================================================================
        # PASO 2: cuanto perturban esos habitos la noche
        #
        # Este es el punto clave del generador. Los habitos no solo restan
        # puntos por formula: en la realidad TAMBIEN alteran el sueno, y el
        # historial ficticio debe reflejarlo.
        #
        # Sin esta relacion, la duracion y las interrupciones se sorteaban de
        # forma completamente independiente de la cafeina, y su variabilidad
        # (que mueve hasta 70 de los 100 puntos del score) ahogaba por completo
        # la senal de la cafeina: el coeficiente de correlacion caia por debajo
        # del umbral en el que la aplicacion lo considera apreciable, y el
        # panel acababa diciendo que la cafeina no afecta al descanso.
        #
        # Modelar el efecto fisiologico no es maquillar los datos: es lo que
        # hace que la correlacion que muestra la aplicacion se corresponda con
        # una causa real presente en el historial. La formula del score no se
        # toca en absoluto.
        # =====================================================================
        # -- Hora de acostarse ------------------------------------------------
        # Se decide aqui, antes de medir la perturbacion, porque el efecto real
        # de la cafeina depende de cuantas HORAS faltaban para dormir, no de la
        # hora del reloj a la que se tomo. Es la misma magnitud que usa la
        # formula del score, asi que causa y penalizacion quedan alineadas.
        #
        # Trasnochar es mucho mas frecuente en fin de semana. Cuando ocurre, la
        # hora cae en la madrugada del dia SIGUIENTE, pero la noche sigue siendo
        # la de `night`: es exactamente el caso que resuelve `app.services.night`.
        after_midnight_probability = 0.45 if is_weekend else 0.12
        after_midnight = allow_after_midnight and rng.random() < after_midnight_probability

        if after_midnight:
            bedtime_minutes = rng.randint(5, 100) if is_weekend else rng.randint(5, 50)
            bedtime_day = night + timedelta(days=1)
        else:
            bedtime_minutes = (
                rng.randint(23 * 60 + 10, 23 * 60 + 55)
                if is_weekend
                else rng.randint(22 * 60 + 15, 23 * 60 + 20)
            )
            bedtime_day = night

        sleep_start = datetime.combine(
            bedtime_day,
            time(hour=bedtime_minutes // 60, minute=bedtime_minutes % 60),
        )

        # -- Perturbacion ------------------------------------------------------
        if has_habits:
            if last_caffeine_time is None:
                caffeine_load = 0.0
            else:
                # Horas reales entre el ultimo cafe y el momento de dormir. El
                # consumo se fecha en `night`, igual que hace el servicio de
                # scoring, de modo que la resta sigue siendo correcta cuando la
                # hora de acostarse cae pasada la medianoche.
                caffeine_at = datetime.combine(night, last_caffeine_time)
                hours_before = (sleep_start - caffeine_at).total_seconds() / 3600.0

                # Misma ventana de 8 horas que la formula del score.
                proximity = _clamp((8.0 - hours_before) / 8.0, 0.0, 1.0)
                caffeine_load = (caffeine_mg / 400.0) * proximity

            screen_load = _clamp((screen_minutes - 30) / 90.0, 0.0, 1.0)
            disruption = _clamp(0.70 * caffeine_load + 0.30 * screen_load, 0.0, 1.0)
        else:
            # Sin habitos registrados, la perturbacion existio igualmente pero
            # no quedo anotada. Se sortea a un nivel intermedio para que esos
            # dias no salgan sistematicamente mejores que el resto.
            disruption = rng.random() * 0.5

        # =====================================================================
        # PASO 3: el resto de la noche
        # =====================================================================

        # -- Duracion ---------------------------------------------------------
        # El rango base es DELIBERADAMENTE ESTRECHO.
        #
        # La duracion mueve 40 de los 100 puntos del score, asi que cada hora
        # de dispersion puramente aleatoria mete mucho ruido. Con un rango
        # ancho, ese ruido ahogaba la senal de los habitos y el coeficiente de
        # correlacion de la cafeina oscilaba entre -0.49 y -0.04 con solo
        # cambiar la semilla: la calidad de la demostracion dependia de la
        # suerte. Estrechando la base y dejando que sea la perturbacion quien
        # mueva la duracion, la relacion se vuelve estable entre semillas.
        base_duration = rng.uniform(7.7, 9.0) if is_weekend else rng.uniform(7.4, 8.5)

        # Una noche muy perturbada recorta mas de dos horas de sueno.
        duration_hours = _clamp(base_duration - disruption * 2.4, 4.8, 9.5)

        sleep_end = sleep_start + timedelta(minutes=round(duration_hours * 60))

        # -- Interrupciones ---------------------------------------------------
        # Distribucion ponderada en lugar de uniforme: lo normal es dormir del
        # tiron y despertarse tres veces es excepcional. La perturbacion
        # desplaza el peso hacia los valores altos de forma acusada.
        base_weights = [40.0, 32.0, 18.0, 10.0] if is_weekend else [60.0, 28.0, 9.0, 3.0]
        weights = [
            base_weights[0] * (1.0 - 0.92 * disruption),
            base_weights[1] * (1.0 + 0.3 * disruption),
            base_weights[2] * (1.0 + 3.5 * disruption),
            base_weights[3] * (1.0 + 7.0 * disruption),
        ]
        interruptions = rng.choices([0, 1, 2, 3], weights=weights)[0]

        # -- Notas ------------------------------------------------------------
        notes = rng.choice(DEMO_NOTES) if rng.random() < 0.28 else None

        return _NightPlan(
            habit_date=night,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            interruptions=interruptions,
            notes=notes,
            caffeine_mg=caffeine_mg,
            last_caffeine_time=last_caffeine_time,
            exercise_minutes=exercise_minutes,
            screen_minutes=screen_minutes,
        )
