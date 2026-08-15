"""Calculo del score de calidad de sueno (0-100).

Este modulo es el nucleo del dominio de SleepMetrics. Es logica PURA: recibe
entidades ya cargadas y devuelve un resultado, sin tocar la base de datos, la
sesion HTTP ni ninguna dependencia externa. Esa pureza es deliberada, porque
convierte la regla de negocio mas importante del sistema en algo que se puede
razonar, verificar a mano y reutilizar desde cualquier contexto.

===============================================================================
FORMULA COMPLETA DEL SCORE
===============================================================================

El score total es la suma de tres componentes ponderados:

    SCORE = DURACION (40 pts) + INTERRUPCIONES (30 pts) + HABITOS (30 pts)

-------------------------------------------------------------------------------
1. DURACION - 40 puntos (peso 40%)
-------------------------------------------------------------------------------
Se parte del consenso clinico de que el rango optimo para un adulto es de 7 a 9
horas. Dentro de ese rango no hay razon para penalizar, asi que la funcion es
una meseta con caidas lineales a ambos lados:

    h en [7, 9]      ->  40 puntos (maximo)
    h < 7            ->  40 * (1 - (7 - h) / 3)     acotado en [0, 40]
    h > 9            ->  40 * (1 - (h - 9) / 3)     acotado en [0, 40]

La tolerancia de 3 horas hace que el componente llegue a 0 en 4 h y en 12 h.
Se penaliza el exceso igual que el defecto porque la hipersomnia se asocia con
peor calidad de descanso, no con mejor.

    Ejemplos:  8.0 h -> 40.00    6.0 h -> 26.67    5.0 h -> 13.33
              10.0 h -> 26.67   12.0 h ->  0.00

-------------------------------------------------------------------------------
2. INTERRUPCIONES - 30 puntos (peso 30%)
-------------------------------------------------------------------------------
Cada despertar fragmenta los ciclos de sueno. La penalizacion es lineal:

    puntos = max(0, 30 - 7.5 * numero_de_interrupciones)

    0 despertares -> 30.0    1 -> 22.5    2 -> 15.0    3 -> 7.5    4 o mas -> 0.0

Se eligio una penalizacion lineal y no exponencial porque el salto de 0 a 1
despertar no es cualitativamente distinto del de 2 a 3: cada interrupcion
cuesta lo mismo hasta agotar el componente.

-------------------------------------------------------------------------------
3. HABITOS - 30 puntos (peso 30%)
-------------------------------------------------------------------------------
Se reparte a partes iguales entre los dos habitos con efecto documentado sobre
la latencia y la arquitectura del sueno:

    3a. CAFEINA TARDIA - 15 puntos
    ------------------------------
    El impacto de la cafeina depende de DOS variables, no de una: cuanta se
    consumio y cuanto falta para dormir. La vida media de la cafeina ronda las
    5-6 horas, asi que 200 mg a las 9:00 son irrelevantes mientras que los
    mismos 200 mg a las 21:00 arruinan la noche.

        factor_cantidad   = min(1, caffeine_mg / 400)
        horas_antes       = sleep_start - hora_del_ultimo_consumo
        factor_proximidad = clamp((8 - horas_antes) / 8, 0, 1)

        puntos = 15 - 15 * factor_cantidad * factor_proximidad

    400 mg es el limite diario que las agencias de seguridad alimentaria
    consideran seguro para un adulto sano: por encima, el factor satura en 1.
    8 horas es la ventana a partir de la cual queda aproximadamente un 25% de
    la dosis en el organismo; consumos anteriores no penalizan.

    Si `last_caffeine_time` es NULL (el usuario no la recuerda) se aplica un
    factor de proximidad de 0.5, equivalente a haberla tomado 4 horas antes de
    dormir. Es un punto medio deliberado: no premia ocultar el dato ni castiga
    a quien simplemente no lo anoto.

        Ejemplos:  0 mg               -> 15.00
                   200 mg, 10 h antes -> 15.00  (fuera de la ventana)
                   200 mg, 4 h antes  -> 11.25
                   400 mg, 2 h antes  ->  3.75
                   400 mg, 0 h antes  ->  0.00

    3b. TIEMPO DE PANTALLA ANTES DE DORMIR - 15 puntos
    --------------------------------------------------
    La luz azul retrasa la secrecion de melatonina. Se admite un margen de 30
    minutos sin penalizacion, y a partir de ahi la caida es lineal hasta
    agotar el componente a los 120 minutos:

        min <= 30   -> 15 puntos
        min >= 120  ->  0 puntos
        intermedio  -> 15 * (1 - (min - 30) / 90)

        Ejemplos:  20 min -> 15.00    60 min -> 10.00
                   90 min ->  5.00   150 min ->  0.00

    NOTA sobre `exercise_minutes`: se registra en la tabla `daily_habits` y se
    muestra en la interfaz, pero NO entra en el score. La especificacion del
    componente de habitos menciona expresamente cafeina y tiempo de pantalla;
    anadir el ejercicio por cuenta propia cambiaria la formula acordada. Queda
    disponible como dato para una version futura del algoritmo.

-------------------------------------------------------------------------------
CASO SIN HABITOS REGISTRADOS
-------------------------------------------------------------------------------
Si no existe registro de habitos para la fecha de la sesion, el componente de
habitos no se puede evaluar. Hay dos salidas malas y una buena:

  - Dar 0 puntos castigaria al usuario por no haber rellenado un formulario.
  - Dar los 30 puntos completos regalaria un score inflado.
  - La correcta: calcular el score sobre los dos componentes disponibles y
    reescalarlo a base 100.

        SCORE = (duracion + interrupciones) / 70 * 100

La respuesta incluye `habits_available: false` para que la interfaz pueda
avisar de que el score es parcial.

-------------------------------------------------------------------------------
EMPAREJAMIENTO SESION - HABITOS
-------------------------------------------------------------------------------
Una sesion se empareja con los habitos de la NOCHE a la que pertenece, que no
siempre coincide con la fecha de `sleep_start`: acostarse a las 00:30 del
martes es la noche del lunes, porque el cafe y las pantallas que influyeron en
ese sueno fueron los del lunes.

La regla completa, con su justificacion y sus casos limite, vive en
`app.services.night`. El servicio de scoring, el de habitos y el de analitica
la comparten para que exista una unica definicion.
"""

from dataclasses import dataclass
from datetime import datetime

from app.models.daily_habit import DailyHabit
from app.models.sleep_session import SleepSession

# ---------------------------------------------------------------------------
# Constantes de la formula
#
# Todos los numeros magicos del algoritmo viven aqui y en ningun otro sitio.
# Ajustar la formula es cambiar estos valores, no perseguir literales sueltos
# repartidos por el codigo.
# ---------------------------------------------------------------------------

# Pesos de los tres componentes principales (deben sumar 100).
DURATION_WEIGHT = 40.0
INTERRUPTIONS_WEIGHT = 30.0
HABITS_WEIGHT = 30.0

# Reparto interno del componente de habitos (debe sumar HABITS_WEIGHT).
CAFFEINE_WEIGHT = 15.0
SCREEN_TIME_WEIGHT = 15.0

# -- Duracion ---------------------------------------------------------------
OPTIMAL_MIN_HOURS = 7.0
OPTIMAL_MAX_HOURS = 9.0
# Horas de desviacion respecto al rango optimo que agotan el componente.
DURATION_TOLERANCE_HOURS = 3.0

# -- Interrupciones ---------------------------------------------------------
PENALTY_PER_INTERRUPTION = 7.5

# -- Cafeina ----------------------------------------------------------------
# Limite diario considerado seguro para un adulto sano (EFSA / FDA).
CAFFEINE_SATURATION_MG = 400.0
# Horas antes de dormir a partir de las cuales la cafeina deja de penalizar.
CAFFEINE_SAFE_WINDOW_HOURS = 8.0
# Factor aplicado cuando se desconoce la hora del consumo.
UNKNOWN_CAFFEINE_TIME_FACTOR = 0.5

# -- Tiempo de pantalla -----------------------------------------------------
SCREEN_TIME_FREE_MINUTES = 30.0
SCREEN_TIME_SATURATION_MINUTES = 120.0


# ---------------------------------------------------------------------------
# Estructuras de resultado
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreComponentResult:
    """Aportacion de un factor concreto al score total."""

    name: str
    points: float
    max_points: float
    detail: str


@dataclass(frozen=True)
class ScoreResult:
    """Resultado completo del calculo, con su desglose.

    Es frozen (inmutable) a proposito: un resultado de calculo no debe poder
    mutarse despues de producirse.
    """

    score: float
    components: list[ScoreComponentResult]
    habits_available: bool
    duration_hours: float


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Acota un valor al intervalo [minimum, maximum]."""
    return max(minimum, min(maximum, value))


def _round2(value: float) -> float:
    """Redondea a 2 decimales, la escala de la columna NUMERIC(5,2)."""
    return round(value + 0.0, 2)


# ---------------------------------------------------------------------------
# Componentes de la formula
# ---------------------------------------------------------------------------

def calculate_duration_component(duration_hours: float) -> ScoreComponentResult:
    """Componente de duracion (0 a 40 puntos).

    Meseta plana en el rango optimo 7-9 h y caidas lineales simetricas a ambos
    lados, que agotan el componente a 3 horas de distancia del rango.
    """
    if OPTIMAL_MIN_HOURS <= duration_hours <= OPTIMAL_MAX_HOURS:
        points = DURATION_WEIGHT
        detail = (
            f"{duration_hours:.1f} h de sueno, dentro del rango optimo "
            f"({OPTIMAL_MIN_HOURS:.0f}-{OPTIMAL_MAX_HOURS:.0f} h)."
        )
    elif duration_hours < OPTIMAL_MIN_HOURS:
        deficit = OPTIMAL_MIN_HOURS - duration_hours
        ratio = _clamp(1.0 - (deficit / DURATION_TOLERANCE_HOURS), 0.0, 1.0)
        points = DURATION_WEIGHT * ratio
        detail = (
            f"{duration_hours:.1f} h de sueno: {deficit:.1f} h por debajo del "
            f"minimo recomendado de {OPTIMAL_MIN_HOURS:.0f} h."
        )
    else:
        excess = duration_hours - OPTIMAL_MAX_HOURS
        ratio = _clamp(1.0 - (excess / DURATION_TOLERANCE_HOURS), 0.0, 1.0)
        points = DURATION_WEIGHT * ratio
        detail = (
            f"{duration_hours:.1f} h de sueno: {excess:.1f} h por encima del "
            f"maximo recomendado de {OPTIMAL_MAX_HOURS:.0f} h."
        )

    return ScoreComponentResult(
        name="Duracion",
        points=_round2(points),
        max_points=DURATION_WEIGHT,
        detail=detail,
    )


def calculate_interruptions_component(interruptions: int) -> ScoreComponentResult:
    """Componente de interrupciones (0 a 30 puntos).

    Penalizacion lineal de 7.5 puntos por despertar; se agota a partir del
    cuarto.
    """
    points = _clamp(
        INTERRUPTIONS_WEIGHT - (PENALTY_PER_INTERRUPTION * interruptions),
        0.0,
        INTERRUPTIONS_WEIGHT,
    )

    if interruptions == 0:
        detail = "Sueno continuo, sin despertares registrados."
    else:
        plural = "despertar" if interruptions == 1 else "despertares"
        detail = (
            f"{interruptions} {plural}: "
            f"-{min(PENALTY_PER_INTERRUPTION * interruptions, INTERRUPTIONS_WEIGHT):.1f} puntos."
        )

    return ScoreComponentResult(
        name="Interrupciones",
        points=_round2(points),
        max_points=INTERRUPTIONS_WEIGHT,
        detail=detail,
    )


def _caffeine_proximity_factor(habit: DailyHabit, sleep_start: datetime) -> tuple[float, str]:
    """Factor de proximidad del ultimo consumo de cafeina al momento de dormir.

    Returns:
        (factor en [0, 1], texto explicativo). 0 = sin impacto, 1 = impacto
        maximo.
    """
    if habit.last_caffeine_time is None:
        # Sin hora conocida se asume un punto medio de la ventana de riesgo.
        return UNKNOWN_CAFFEINE_TIME_FACTOR, "hora de consumo desconocida"

    # La hora se combina con la fecha del registro de habitos para obtener un
    # instante comparable con sleep_start. Si el usuario se durmio pasada la
    # medianoche, sleep_start cae en el dia siguiente y la resta sigue siendo
    # correcta (por ejemplo: cafe a las 22:00 del dia 14, sueno a las 00:30 del
    # dia 15 -> 2.5 horas).
    caffeine_at = datetime.combine(habit.date, habit.last_caffeine_time)
    hours_before = (sleep_start - caffeine_at).total_seconds() / 3600.0

    if hours_before < 0:
        # Consumo posterior al inicio del sueno: dato incoherente o cafeina
        # tomada en mitad de la noche. Se trata como impacto maximo.
        return 1.0, "consumo posterior a la hora de acostarse"

    factor = _clamp(
        (CAFFEINE_SAFE_WINDOW_HOURS - hours_before) / CAFFEINE_SAFE_WINDOW_HOURS,
        0.0,
        1.0,
    )
    return factor, f"ultimo consumo {hours_before:.1f} h antes de dormir"


def calculate_caffeine_component(
    habit: DailyHabit,
    sleep_start: datetime,
) -> ScoreComponentResult:
    """Sub-componente de cafeina (0 a 15 puntos).

    Combina cantidad y proximidad temporal: ninguna de las dos por separado
    describe el impacto real.
    """
    amount_factor = _clamp(habit.caffeine_mg / CAFFEINE_SATURATION_MG, 0.0, 1.0)
    proximity_factor, proximity_detail = _caffeine_proximity_factor(habit, sleep_start)

    penalty = CAFFEINE_WEIGHT * amount_factor * proximity_factor
    points = _clamp(CAFFEINE_WEIGHT - penalty, 0.0, CAFFEINE_WEIGHT)

    if habit.caffeine_mg == 0:
        detail = "Sin consumo de cafeina registrado."
    elif penalty < 0.01:
        detail = (
            f"{habit.caffeine_mg} mg de cafeina, pero {proximity_detail}: "
            "fuera de la ventana de impacto."
        )
    else:
        detail = (
            f"{habit.caffeine_mg} mg de cafeina, {proximity_detail}: "
            f"-{penalty:.1f} puntos."
        )

    return ScoreComponentResult(
        name="Cafeina",
        points=_round2(points),
        max_points=CAFFEINE_WEIGHT,
        detail=detail,
    )


def calculate_screen_time_component(habit: DailyHabit) -> ScoreComponentResult:
    """Sub-componente de tiempo de pantalla antes de dormir (0 a 15 puntos).

    Margen libre de 30 minutos y caida lineal hasta agotarse en 120 minutos.
    """
    minutes = float(habit.screen_time_before_bed_minutes)

    if minutes <= SCREEN_TIME_FREE_MINUTES:
        points = SCREEN_TIME_WEIGHT
        detail = f"{minutes:.0f} min de pantalla antes de dormir, dentro del margen aceptable."
    else:
        excess = minutes - SCREEN_TIME_FREE_MINUTES
        span = SCREEN_TIME_SATURATION_MINUTES - SCREEN_TIME_FREE_MINUTES
        ratio = _clamp(1.0 - (excess / span), 0.0, 1.0)
        points = SCREEN_TIME_WEIGHT * ratio
        detail = (
            f"{minutes:.0f} min de pantalla antes de dormir: "
            f"-{SCREEN_TIME_WEIGHT - points:.1f} puntos."
        )

    return ScoreComponentResult(
        name="Tiempo de pantalla",
        points=_round2(points),
        max_points=SCREEN_TIME_WEIGHT,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Entrada publica del servicio
# ---------------------------------------------------------------------------

def calculate_sleep_score(
    session: SleepSession,
    habit: DailyHabit | None,
) -> ScoreResult:
    """Calcula el score de calidad de una sesion de sueno.

    Args:
        session: la sesion a evaluar.
        habit: habitos registrados para la fecha de `session.sleep_start`, o
            None si el usuario no los registro ese dia.

    Returns:
        ScoreResult con el score final (0-100), el desglose por componente y la
        marca `habits_available`.
    """
    duration_hours = session.duration_hours

    # -- Componentes siempre disponibles ------------------------------------
    duration_component = calculate_duration_component(duration_hours)
    interruptions_component = calculate_interruptions_component(session.interruptions)

    components = [duration_component, interruptions_component]
    base_points = duration_component.points + interruptions_component.points

    # -- Componente de habitos ----------------------------------------------
    if habit is None:
        # Sin habitos no se puede evaluar el 30% restante. Se reescala el score
        # sobre los dos componentes disponibles para no castigar ni inflar.
        available_max = DURATION_WEIGHT + INTERRUPTIONS_WEIGHT
        final_score = _clamp((base_points / available_max) * 100.0, 0.0, 100.0)

        return ScoreResult(
            score=_round2(final_score),
            components=components,
            habits_available=False,
            duration_hours=_round2(duration_hours),
        )

    caffeine_component = calculate_caffeine_component(habit, session.sleep_start)
    screen_component = calculate_screen_time_component(habit)
    components.extend([caffeine_component, screen_component])

    total = base_points + caffeine_component.points + screen_component.points
    final_score = _clamp(total, 0.0, 100.0)

    return ScoreResult(
        score=_round2(final_score),
        components=components,
        habits_available=True,
        duration_hours=_round2(duration_hours),
    )
