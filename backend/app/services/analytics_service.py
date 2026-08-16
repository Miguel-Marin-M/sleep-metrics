"""Logica de negocio de la analitica: agregados, tendencias y correlaciones."""

from collections import defaultdict
from datetime import date as date_type
from datetime import datetime, timedelta
from math import sqrt

from app.models.daily_habit import DailyHabit
from app.models.sleep_session import SleepSession
from app.repositories.daily_habit_repository import DailyHabitRepository
from app.repositories.sleep_session_repository import SleepSessionRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    Correlation,
    PeriodAverage,
    ScoreComponent,
    SessionScoreResponse,
    WeekdayAverage,
)
from app.services.night import night_date
from app.services.sleep_session_service import SleepSessionService

# Nombres de los dias de la semana indexados como los devuelve
# `datetime.weekday()`: 0 = lunes ... 6 = domingo.
WEEKDAY_NAMES = [
    "Lunes",
    "Martes",
    "Miercoles",
    "Jueves",
    "Viernes",
    "Sabado",
    "Domingo",
]

# Numero minimo de pares (habito, score) para calcular una correlacion.
#
# El umbral estuvo en 5 y se subio a 14 (dos semanas de registro) por evidencia
# medida, no por intuicion: al construir el generador de datos de demostracion
# se barrieron diez semillas sobre un historial que contenia una relacion causal
# REAL y fuerte entre cafeina y calidad del sueno. Con unas 30 muestras el
# coeficiente de Pearson oscilaba entre -0.60 y +0.07 solo por el azar del
# muestreo.
#
# Si con 30 muestras y una causa real el coeficiente baila asi, con 5 lo que se
# publica es ruido. Y no es ruido inocuo: la aplicacion lo presenta con una
# frase afirmativa ("cuanto mayor es la cafeina, peor tiende a ser tu score"), de
# modo que un usuario podria cambiar sus habitos por una casualidad estadistica.
# En una aplicacion relacionada con la salud, ese es el error caro.
MIN_CORRELATION_SAMPLES = 14

# Numero de muestras a partir del cual la correlacion deja de anunciarse como
# preliminar.
#
# Entre MIN_CORRELATION_SAMPLES y este valor el coeficiente ya es informativo
# pero sigue siendo inestable, asi que se calcula y se muestra acompanado de una
# advertencia explicita en lugar de con lenguaje afirmativo. Es el punto medio
# honesto entre no ensenar nada durante un mes y afirmar de mas.
RELIABLE_CORRELATION_SAMPLES = 30

# Sesiones minimas en un mismo dia de la semana para que ese dia pueda ser
# elegido como el mejor o el peor.
#
# Con una sola noche registrada en cada dia, "tu mejor dia es el miercoles" no
# describe un patron: describe que el miercoles pasado se durmio bien. Exigir
# tres repeticiones convierte la afirmacion en algo que empieza a significar
# alguna cosa.
MIN_WEEKDAY_SESSIONS = 3


class AnalyticsService:
    """Casos de uso de analitica sobre el historial del usuario.

    Depende de `SleepSessionService` en lugar de duplicar su logica: el
    recalculo de un score ya esta resuelto alli, y reimplementarlo aqui
    generaria dos fuentes de verdad del mismo comportamiento.
    """

    def __init__(
        self,
        session_repository: SleepSessionRepository,
        habit_repository: DailyHabitRepository,
        session_service: SleepSessionService,
    ) -> None:
        self.session_repository = session_repository
        self.habit_repository = habit_repository
        self.session_service = session_service

    # -----------------------------------------------------------------------
    # GET /analytics/score/{session_id}
    # -----------------------------------------------------------------------

    def get_session_score(self, user_id: int, session_id: int) -> SessionScoreResponse:
        """Recalcula el score de una sesion y devuelve su desglose completo.

        Recalcula en vez de leer el valor almacenado a proposito: es el
        endpoint que el usuario consulta cuando quiere entender su score, y
        entre la creacion de la sesion y esa consulta pueden haberse registrado
        los habitos del dia. El resultado se persiste, de modo que el historial
        tambien queda actualizado.
        """
        session, score_result = self.session_service.recalculate_score(user_id, session_id)

        # El instante de calculo se lee de la fila persistida para que el
        # cliente vea exactamente la misma marca temporal que hay en la base de
        # datos, sin desfases por recalcularla en Python.
        stored_score = self.session_service.score_repository.get_by_session_id(session.id)
        calculated_at = (
            stored_score.calculated_at if stored_score is not None else datetime.now()
        )

        return SessionScoreResponse(
            session_id=session.id,
            score=score_result.score,
            calculated_at=calculated_at,
            components=[
                ScoreComponent(
                    name=component.name,
                    points=component.points,
                    max_points=component.max_points,
                    detail=component.detail,
                )
                for component in score_result.components
            ],
            habits_available=score_result.habits_available,
            duration_hours=score_result.duration_hours,
        )

    # -----------------------------------------------------------------------
    # GET /analytics/summary
    # -----------------------------------------------------------------------

    def get_summary(self, user_id: int) -> AnalyticsSummary:
        """Resumen analitico del historial completo del usuario.

        Se carga todo el historial de una vez (dos consultas: sesiones y
        habitos) y se agrega en memoria. Es la estrategia correcta para este
        dominio: un usuario genera como mucho una sesion al dia, asi que
        incluso tras anos de uso el conjunto cabe holgadamente en memoria, y
        resolverlo con agregados SQL exigiria una consulta distinta por metrica.
        """
        sessions = self.session_repository.list_all_for_user(user_id)
        habits = self.habit_repository.list_all_for_user(user_id)

        # Indice de habitos por fecha: convierte la busqueda de los habitos de
        # cada sesion en O(1) y evita el patron N+1.
        habits_by_date: dict[date_type, DailyHabit] = {habit.date: habit for habit in habits}

        # El limite de las ventanas temporales se calcula con la hora del
        # servidor. Las marcas de tiempo del dominio son locales del usuario
        # (TIMESTAMP sin zona), asi que un usuario en un huso muy alejado podria
        # ver una sesion entrar o salir de la ventana de 7 dias por unas horas.
        # Es una imprecision asumida y acotada: manejar husos por usuario
        # requeriria almacenar su zona horaria, algo fuera del alcance actual.
        now = datetime.now()

        return AnalyticsSummary(
            total_sessions=len(sessions),
            last_7_days=self._period_average(sessions, now, days=7),
            last_30_days=self._period_average(sessions, now, days=30),
            average_score=self._average_score(sessions),
            best_weekday=self._best_weekday(sessions),
            worst_weekday=self._worst_weekday(sessions),
            correlations=self._correlations(sessions, habits_by_date),
        )

    # -----------------------------------------------------------------------
    # Metricas individuales
    # -----------------------------------------------------------------------

    @staticmethod
    def _period_average(
        sessions: list[SleepSession],
        now: datetime,
        days: int,
    ) -> PeriodAverage:
        """Promedio de horas dormidas en los ultimos `days` dias."""
        cutoff = now - timedelta(days=days)
        window = [s for s in sessions if s.sleep_start >= cutoff]

        if not window:
            # None y no 0.0: "no hay datos" y "dormiste 0 horas" son cosas
            # distintas, y el frontend debe poder distinguirlas.
            return PeriodAverage(days=days, average_hours=None, sessions_count=0)

        total_hours = sum(s.duration_hours for s in window)
        return PeriodAverage(
            days=days,
            average_hours=round(total_hours / len(window), 2),
            sessions_count=len(window),
        )

    @staticmethod
    def _scored_sessions(sessions: list[SleepSession]) -> list[tuple[SleepSession, float]]:
        """Filtra las sesiones que ya tienen score y lo devuelve como float.

        El score se persiste como NUMERIC (Decimal en Python); se convierte a
        float aqui, en un unico punto, para no repetir la conversion en cada
        metrica.
        """
        return [
            (session, float(session.score.score))
            for session in sessions
            if session.score is not None
        ]

    def _average_score(self, sessions: list[SleepSession]) -> float | None:
        """Score medio historico del usuario."""
        scored = self._scored_sessions(sessions)
        if not scored:
            return None
        return round(sum(score for _, score in scored) / len(scored), 2)

    def _weekday_averages(self, sessions: list[SleepSession]) -> list[WeekdayAverage]:
        """Score medio agrupado por dia de la semana.

        El dia se toma de la NOCHE a la que pertenece la sesion, no de la fecha
        cruda de `sleep_start`. La diferencia importa justo donde el usuario
        espera que importe: quien se acuesta el viernes a las 00:30 esta
        durmiendo la noche del jueves, y contabilizarla como viernes desplazaria
        sistematicamente el mejor y el peor dia de la semana.
        """
        scored = self._scored_sessions(sessions)
        if not scored:
            return []

        buckets: dict[int, list[float]] = defaultdict(list)
        for session, score in scored:
            buckets[night_date(session.sleep_start).weekday()].append(score)

        return [
            WeekdayAverage(
                weekday=weekday,
                weekday_name=WEEKDAY_NAMES[weekday],
                average_score=round(sum(scores) / len(scores), 2),
                sessions_count=len(scores),
            )
            for weekday, scores in sorted(buckets.items())
        ]

    def _eligible_weekdays(self, sessions: list[SleepSession]) -> list[WeekdayAverage]:
        """Dias de la semana con repeticiones suficientes para ser comparados.

        Se descartan los que no llegan a MIN_WEEKDAY_SESSIONS. Sin este filtro,
        un usuario con una semana de historial veria "tu peor dia es el martes"
        basado en una unica noche, que es una anecdota presentada como patron.
        """
        return [
            average
            for average in self._weekday_averages(sessions)
            if average.sessions_count >= MIN_WEEKDAY_SESSIONS
        ]

    def _best_weekday(self, sessions: list[SleepSession]) -> WeekdayAverage | None:
        """Dia de la semana con mejor score medio.

        Devuelve None mientras ningun dia acumule repeticiones suficientes; el
        frontend muestra entonces "Sin datos" en lugar de una conclusion
        prematura.
        """
        eligible = self._eligible_weekdays(sessions)
        if not eligible:
            return None
        return max(eligible, key=lambda item: item.average_score)

    def _worst_weekday(self, sessions: list[SleepSession]) -> WeekdayAverage | None:
        """Dia de la semana con peor score medio."""
        eligible = self._eligible_weekdays(sessions)
        if not eligible:
            return None
        return min(eligible, key=lambda item: item.average_score)

    # -----------------------------------------------------------------------
    # Correlaciones
    # -----------------------------------------------------------------------

    def _correlations(
        self,
        sessions: list[SleepSession],
        habits_by_date: dict[date_type, DailyHabit],
    ) -> list[Correlation]:
        """Correlacion entre cada habito y el score de sueno.

        Solo entran en el analisis las sesiones que tienen score Y habitos
        registrados para su fecha: un par incompleto no aporta informacion y
        sesgaria el coeficiente.
        """
        caffeine_pairs: list[tuple[float, float]] = []
        screen_pairs: list[tuple[float, float]] = []
        exercise_pairs: list[tuple[float, float]] = []

        for session, score in self._scored_sessions(sessions):
            habit = habits_by_date.get(night_date(session.sleep_start))
            if habit is None:
                continue

            caffeine_pairs.append((float(habit.caffeine_mg), score))
            screen_pairs.append((float(habit.screen_time_before_bed_minutes), score))
            exercise_pairs.append((float(habit.exercise_minutes), score))

        return [
            self._build_correlation("Cafeina (mg)", caffeine_pairs),
            self._build_correlation("Tiempo de pantalla (min)", screen_pairs),
            self._build_correlation("Ejercicio (min)", exercise_pairs),
        ]

    def _build_correlation(self, factor: str, pairs: list[tuple[float, float]]) -> Correlation:
        """Construye el resultado de correlacion de un factor."""
        coefficient = self._pearson(pairs)

        return Correlation(
            factor=factor,
            coefficient=coefficient,
            sample_size=len(pairs),
            interpretation=self._interpret(factor, coefficient, len(pairs)),
        )

    @staticmethod
    def _pearson(pairs: list[tuple[float, float]]) -> float | None:
        """Coeficiente de correlacion lineal de Pearson.

        Se implementa a mano en lugar de traer numpy o scipy: son dependencias
        de decenas de megabytes para una formula de cinco lineas, y el free tier
        de Render tiene un limite estrecho de memoria y de tiempo de build.

                    sum((x - mx) * (y - my))
            r = ---------------------------------------
                sqrt(sum((x-mx)^2) * sum((y-my)^2))

        Returns:
            El coeficiente en [-1, 1], o None si no hay muestras suficientes o
            si alguna de las variables es constante (varianza cero: en ese caso
            la correlacion es matematicamente indefinida, no cero).
        """
        n = len(pairs)
        if n < MIN_CORRELATION_SAMPLES:
            return None

        xs = [x for x, _ in pairs]
        ys = [y for _, y in pairs]

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        covariance = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
        variance_x = sum((x - mean_x) ** 2 for x in xs)
        variance_y = sum((y - mean_y) ** 2 for y in ys)

        if variance_x == 0 or variance_y == 0:
            # Variable constante: por ejemplo, el usuario registro siempre 0 mg
            # de cafeina. No hay variacion que correlacionar.
            return None

        return round(covariance / sqrt(variance_x * variance_y), 3)

    @staticmethod
    def _interpret(factor: str, coefficient: float | None, sample_size: int) -> str:
        """Traduce el coeficiente a una frase entendible.

        Un numero como -0.62 no le dice nada a un usuario no tecnico. Esta
        traduccion es lo que convierte la metrica en algo accionable.
        """
        if coefficient is None:
            if sample_size < MIN_CORRELATION_SAMPLES:
                faltan = MIN_CORRELATION_SAMPLES - sample_size
                noches = "noche" if faltan == 1 else "noches"
                return (
                    f"Aun no hay datos suficientes: faltan {faltan} {noches} con habitos "
                    "y sueno registrados el mismo dia. Con menos, el resultado seria azar."
                )
            return "Sin variacion suficiente en este habito para analizar su efecto."

        magnitude = abs(coefficient)

        # Entre el minimo y el umbral de fiabilidad el coeficiente ya es
        # informativo pero todavia inestable, asi que se antepone una
        # advertencia y NUNCA se usa lenguaje afirmativo.
        preliminary = sample_size < RELIABLE_CORRELATION_SAMPLES
        prefix = "Tendencia preliminar. " if preliminary else ""

        if magnitude < 0.2:
            return (
                f"{prefix}Sin relacion apreciable entre {factor.lower()} y tu calidad "
                "de sueno."
            )

        if magnitude < 0.4:
            strength = "debil"
        elif magnitude < 0.7:
            strength = "moderada"
        else:
            strength = "fuerte"

        direction = "peor" if coefficient < 0 else "mejor"
        relation = "inversa" if coefficient < 0 else "directa"

        if preliminary:
            # Formulacion tentativa: describe lo observado hasta ahora y avisa
            # de que puede cambiar, en lugar de enunciar una regla.
            return (
                f"Tendencia preliminar ({sample_size} noches): por ahora, a mayor "
                f"{factor.lower()} tu score tiende a ser {direction}. Necesita mas "
                "registros para confirmarse."
            )

        return (
            f"Relacion {relation} {strength}: cuanto mayor es {factor.lower()}, "
            f"{direction} tiende a ser tu score."
        )
