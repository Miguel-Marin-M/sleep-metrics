/**
 * Utilidades de formato y presentacion.
 *
 * Todas las conversiones de "dato crudo" a "texto para el usuario" viven aqui.
 * Concentrarlas evita que la misma fecha aparezca con tres formatos distintos
 * en tres pantallas distintas.
 */

/** Locale unico de la aplicacion. */
const LOCALE = 'es-ES'

// ---------------------------------------------------------------------------
// Fechas y horas
// ---------------------------------------------------------------------------

/**
 * Convierte una cadena ISO sin zona horaria en un objeto Date local.
 *
 * Detalle que importa: el backend envia marcas de tiempo SIN offset (por
 * ejemplo "2026-08-14T23:30:00") porque el dominio del sueno es local. El
 * constructor `new Date()` interpreta correctamente ese formato como hora
 * local. Si la cadena llevara una "Z" al final, el navegador la trataria como
 * UTC y la desplazaria segun el huso del usuario, mostrando una hora de
 * acostarse equivocada. Por eso se elimina cualquier marca de zona antes de
 * construir la fecha.
 */
export function parseLocalDateTime(isoString: string): Date {
  const withoutTimezone = isoString.replace(/(Z|[+-]\d{2}:?\d{2})$/, '')
  return new Date(withoutTimezone)
}

/** Fecha corta: "14 ago 2026". */
export function formatDate(isoString: string): string {
  return parseLocalDateTime(isoString).toLocaleDateString(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** Fecha y hora: "14 ago 2026, 23:30". */
export function formatDateTime(isoString: string): string {
  return parseLocalDateTime(isoString).toLocaleString(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Solo la hora: "23:30". */
export function formatTime(isoString: string): string {
  return parseLocalDateTime(isoString).toLocaleTimeString(LOCALE, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Etiqueta corta para el eje X de las graficas: "jue 14". */
export function formatAxisDate(isoString: string): string {
  return parseLocalDateTime(isoString).toLocaleDateString(LOCALE, {
    weekday: 'short',
    day: 'numeric',
  })
}

/** Fecha de hoy en formato YYYY-MM-DD, apta para un input type="date". */
export function todayAsInputValue(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/**
 * Instante actual en formato YYYY-MM-DDTHH:mm, apto para datetime-local.
 *
 * No se puede usar `toISOString()`: convierte a UTC y desplazaria la hora
 * segun el huso del navegador. Se construye componente a componente en hora
 * local, que es lo que el input espera.
 */
export function nowAsInputValue(offsetHours = 0): string {
  const now = new Date()
  now.setHours(now.getHours() + offsetHours)

  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')

  return `${now.getFullYear()}-${month}-${day}T${hours}:${minutes}`
}

// ---------------------------------------------------------------------------
// Noches
// ---------------------------------------------------------------------------

/**
 * Hora de corte que separa una noche de la siguiente.
 *
 * DEBE COINCIDIR con NIGHT_CUTOFF_HOUR del backend (app/services/night.py).
 * La regla se duplica aqui porque el formulario necesita adelantar el
 * resultado ANTES de enviar nada al servidor; si divergieran, la interfaz
 * prometeria una noche y el backend calcularia otra.
 */
const NIGHT_CUTOFF_HOUR = 12

/**
 * Devuelve la fecha (YYYY-MM-DD) de la noche a la que pertenece una hora de
 * acostarse.
 *
 * Acostarse a partir del mediodia pertenece a la noche de ese mismo dia;
 * antes del mediodia, a la del dia anterior. Asi, dormirse a las 23:30 del
 * viernes y a las 00:30 del sabado son ambas "la noche del viernes".
 *
 * @param localDateTime valor de un input datetime-local ("2026-08-15T00:30")
 * @returns fecha de la noche, o null si la entrada no es valida
 */
export function nightDateOf(localDateTime: string): string | null {
  if (!localDateTime) return null

  const moment = new Date(localDateTime)
  if (Number.isNaN(moment.getTime())) return null

  if (moment.getHours() < NIGHT_CUTOFF_HOUR) {
    moment.setDate(moment.getDate() - 1)
  }

  const month = String(moment.getMonth() + 1).padStart(2, '0')
  const day = String(moment.getDate()).padStart(2, '0')
  return `${moment.getFullYear()}-${month}-${day}`
}

/**
 * Describe el tramo real que cubre una noche: "Del viernes 14 ago por la
 * noche al sabado 15 ago por la manana".
 *
 * Sirve para eliminar la duda de que significa la fecha en el formulario de
 * habitos, que es justo donde la convencion resulta menos evidente.
 */
export function describeNight(isoDate: string): string {
  const start = parseLocalDateTime(`${isoDate}T00:00:00`)
  if (Number.isNaN(start.getTime())) return ''

  const end = new Date(start)
  end.setDate(end.getDate() + 1)

  const label = (value: Date) =>
    value.toLocaleDateString(LOCALE, { weekday: 'long', day: 'numeric', month: 'short' })

  return `Del ${label(start)} por la noche al ${label(end)} por la manana.`
}

// ---------------------------------------------------------------------------
// Numeros
// ---------------------------------------------------------------------------

/** Duracion en horas y minutos: 7.53 -> "7 h 32 min". */
export function formatDuration(hours: number): string {
  const wholeHours = Math.floor(hours)
  const minutes = Math.round((hours - wholeHours) * 60)

  // Redondear los minutos puede llegar a 60; se normaliza para no mostrar
  // "7 h 60 min".
  if (minutes === 60) {
    return `${wholeHours + 1} h 0 min`
  }

  return `${wholeHours} h ${minutes} min`
}

/** Horas con un decimal: "7,5 h". */
export function formatHours(hours: number | null): string {
  if (hours === null) return 'Sin datos'
  return `${hours.toFixed(1).replace('.', ',')} h`
}

/** Score sin decimales innecesarios: 87.5 -> "88". */
export function formatScore(score: number | null): string {
  if (score === null) return '-'
  return String(Math.round(score))
}

// ---------------------------------------------------------------------------
// Interpretacion del score
// ---------------------------------------------------------------------------

export type ScoreLevel = 'good' | 'warning' | 'serious' | 'critical'

/**
 * Clasifica un score numerico en un nivel cualitativo.
 *
 * Los cortes son los mismos que usa la interfaz para elegir color Y etiqueta.
 * Es deliberado que siempre viajen juntos: el color por si solo no puede
 * transmitir la informacion, porque un usuario con deficiencia en la vision
 * del color no la percibiria.
 */
export function getScoreLevel(score: number): ScoreLevel {
  if (score >= 80) return 'good'
  if (score >= 60) return 'warning'
  if (score >= 40) return 'serious'
  return 'critical'
}

/** Etiqueta de texto del nivel. Acompana SIEMPRE al color. */
export function getScoreLabel(score: number): string {
  const labels: Record<ScoreLevel, string> = {
    good: 'Excelente',
    warning: 'Aceptable',
    serious: 'Mejorable',
    critical: 'Deficiente',
  }
  return labels[getScoreLevel(score)]
}

/** Clases de Tailwind para el nivel de un score (fondo, texto y borde). */
export function getScoreClasses(score: number): string {
  const classes: Record<ScoreLevel, string> = {
    good: 'bg-status-good/10 text-[#0a7d0a] border-status-good/30',
    warning: 'bg-status-warning/15 text-[#8a5d00] border-status-warning/40',
    serious: 'bg-status-serious/15 text-[#a24a22] border-status-serious/40',
    critical: 'bg-status-critical/10 text-[#a52d2d] border-status-critical/30',
  }
  return classes[getScoreLevel(score)]
}

/**
 * Color solido del nivel, para marcas graficas (no para texto).
 *
 * El texto nunca lleva el color del dato: usa siempre tokens de tinta. Estos
 * valores son para arcos, barras y puntos.
 */
export function getScoreColor(score: number): string {
  const colors: Record<ScoreLevel, string> = {
    good: '#0ca30c',
    warning: '#fab219',
    serious: '#ec835a',
    critical: '#d03b3b',
  }
  return colors[getScoreLevel(score)]
}
