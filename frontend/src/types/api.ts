/**
 * Tipos TypeScript que reflejan los schemas Pydantic del backend.
 *
 * Son el contrato compartido entre las dos mitades del proyecto. Mantenerlos
 * alineados con `backend/app/schemas/` es lo que permite que un cambio en la
 * API se manifieste como un error de compilacion en el frontend, en lugar de
 * como un `undefined` en tiempo de ejecucion delante del usuario.
 */

// ---------------------------------------------------------------------------
// Autenticacion
// ---------------------------------------------------------------------------

export interface User {
  id: number
  name: string
  email: string
  created_at: string
  /**
   * true en las cuentas desechables creadas por POST /auth/demo.
   *
   * El frontend lo usa para avisar de que los datos son ficticios y de que la
   * cuenta se eliminara sola, para que nadie confunda la demostracion con una
   * cuenta real y registre ahi datos que quiera conservar.
   */
  is_demo: boolean
}

export interface RegisterPayload {
  name: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

/**
 * Respuesta de /auth/register y /auth/login.
 *
 * No contiene el token: el JWT viaja en una cookie httpOnly que emite el
 * backend y que el JavaScript de esta aplicacion no puede leer. Es intencional.
 */
export interface AuthResponse {
  user: User
  message: string
}

export interface MessageResponse {
  message: string
}

// ---------------------------------------------------------------------------
// Sesiones de sueno
// ---------------------------------------------------------------------------

export interface SleepSession {
  id: number
  user_id: number
  /** ISO 8601 sin zona horaria, en hora local del usuario. */
  sleep_start: string
  sleep_end: string
  interruptions: number
  notes: string | null
  created_at: string
  duration_hours: number
  /** null solo si el score aun no se calculo. */
  score: number | null
}

export interface SleepSessionPayload {
  sleep_start: string
  sleep_end: string
  interruptions: number
  notes?: string | null
}

// ---------------------------------------------------------------------------
// Habitos diarios
// ---------------------------------------------------------------------------

export interface DailyHabit {
  id: number
  user_id: number
  /** Fecha ISO (YYYY-MM-DD). */
  date: string
  caffeine_mg: number
  /** Hora HH:MM:SS, o null si el usuario no la recuerda. */
  last_caffeine_time: string | null
  exercise_minutes: number
  screen_time_before_bed_minutes: number
  created_at: string
}

export interface DailyHabitPayload {
  date: string
  caffeine_mg: number
  last_caffeine_time?: string | null
  exercise_minutes: number
  screen_time_before_bed_minutes: number
}

// ---------------------------------------------------------------------------
// Analitica
// ---------------------------------------------------------------------------

export interface ScoreComponent {
  name: string
  points: number
  max_points: number
  detail: string
}

export interface SessionScore {
  session_id: number
  score: number
  calculated_at: string
  components: ScoreComponent[]
  /** false si no habia habitos registrados: el score es parcial. */
  habits_available: boolean
  duration_hours: number
}

export interface PeriodAverage {
  days: number
  /** null cuando no hay sesiones en la ventana. */
  average_hours: number | null
  sessions_count: number
}

export interface WeekdayAverage {
  /** 0 = lunes ... 6 = domingo. */
  weekday: number
  weekday_name: string
  average_score: number
  sessions_count: number
}

export interface Correlation {
  factor: string
  /** Coeficiente de Pearson en [-1, 1]; null si faltan muestras. */
  coefficient: number | null
  sample_size: number
  interpretation: string
}

export interface AnalyticsSummary {
  total_sessions: number
  last_7_days: PeriodAverage
  last_30_days: PeriodAverage
  average_score: number | null
  best_weekday: WeekdayAverage | null
  worst_weekday: WeekdayAverage | null
  correlations: Correlation[]
}

// ---------------------------------------------------------------------------
// Errores
// ---------------------------------------------------------------------------

/** Cuerpo de error que devuelve FastAPI. */
export interface ApiErrorBody {
  /**
   * FastAPI devuelve una cadena en los errores de negocio, pero un array de
   * objetos en los errores de validacion de Pydantic (422). El tipo refleja esa
   * dualidad para forzar a tratar ambos casos al normalizar el mensaje.
   */
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>
}
