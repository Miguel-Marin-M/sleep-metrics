"""A que noche pertenece una sesion de sueno.

Este modulo define UNA sola regla del dominio, pero es una regla transversal:
la usan el calculo del score, el registro de habitos y toda la analitica. Vive
aparte precisamente para que exista una unica definicion y no tres copias que
puedan divergir.

EL PROBLEMA
-----------
Una sesion de sueno tiene una marca de inicio (`sleep_start`) y hay que
decidir a que "noche" corresponde, porque es esa noche la que se empareja con
los habitos del dia y la que se agrupa por dia de la semana.

La respuesta ingenua es usar directamente la fecha de `sleep_start`. Funciona
mientras uno se acueste antes de medianoche, y se rompe en cuanto la cruza:

    Te acuestas el viernes a las 23:30  ->  fecha viernes    (correcto)
    Te acuestas el sabado a las 00:05   ->  fecha sabado     (INCORRECTO)

En el segundo caso, el cafe y las pantallas que afectaron a esa noche son los
del VIERNES, pero el sistema pedia registrarlos bajo el sabado. Ademas, dos
noches consecutivas podian reclamar la misma fecha: dormirse a las 00:05 del
sabado y despues a las 23:30 del sabado daba dos sesiones compitiendo por un
unico registro de habitos.

LA REGLA
--------
Una sesion pertenece a la noche del dia en que empezo la VELADA, no del dia
del reloj:

    sleep_start a las 12:00 o mas tarde  ->  la noche de ESE dia
    sleep_start antes de las 12:00       ->  la noche del dia ANTERIOR

    Viernes 23:30  ->  noche del viernes
    Sabado  00:05  ->  noche del viernes
    Sabado  23:30  ->  noche del sabado

Con ella, "la noche del viernes" significa lo mismo para el usuario que para
el sistema, y dos noches consecutivas nunca pueden colisionar: cada franja de
24 horas que va del mediodia al mediodia siguiente contiene exactamente una
noche.

POR QUE EL MEDIODIA COMO CORTE
------------------------------
Es el punto mas alejado de cualquier hora plausible de acostarse, asi que
ninguna decision real cae cerca del limite. Un corte a las 18:00 o a las 20:00
clasificaria mal una siesta larga o un acostarse muy temprano por enfermedad.
"""

from datetime import date as date_type
from datetime import datetime, timedelta

# Hora que separa una noche de la siguiente. Acostarse a esta hora o despues
# pertenece a la noche del mismo dia; antes, a la del dia anterior.
NIGHT_CUTOFF_HOUR = 12


def night_date(sleep_start: datetime) -> date_type:
    """Devuelve la fecha de la noche a la que pertenece una sesion de sueno.

    Args:
        sleep_start: momento en que el usuario se durmio.

    Returns:
        La fecha con la que se identifica esa noche, y por tanto la fecha bajo
        la que deben registrarse sus habitos.

    Ejemplos:
        >>> night_date(datetime(2026, 8, 14, 23, 30))
        datetime.date(2026, 8, 14)
        >>> night_date(datetime(2026, 8, 15, 0, 5))
        datetime.date(2026, 8, 14)
        >>> night_date(datetime(2026, 8, 15, 23, 30))
        datetime.date(2026, 8, 15)
    """
    if sleep_start.hour >= NIGHT_CUTOFF_HOUR:
        return sleep_start.date()

    return sleep_start.date() - timedelta(days=1)
