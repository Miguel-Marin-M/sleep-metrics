/**
 * Capa de servicios del frontend: una funcion tipada por endpoint de la API.
 *
 * Los componentes llaman a estas funciones y nunca a `api.get(...)` directo.
 * La razon es la misma que en el backend: si una ruta cambia, se corrige en un
 * unico archivo en lugar de perseguir cadenas repartidas por los componentes.
 */

import { api } from '@/lib/api'
import type {
  AnalyticsSummary,
  AuthResponse,
  DailyHabit,
  DailyHabitPayload,
  LoginPayload,
  MessageResponse,
  RegisterPayload,
  SessionScore,
  SleepSession,
  SleepSessionPayload,
  User,
} from '@/types/api'

// ---------------------------------------------------------------------------
// Autenticacion
// ---------------------------------------------------------------------------

export const authService = {
  /** Crea una cuenta. El backend emite la cookie de sesion en la respuesta. */
  async register(payload: RegisterPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/auth/register', payload)
    return data
  },

  /** Inicia sesion. El backend emite la cookie httpOnly. */
  async login(payload: LoginPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/auth/login', payload)
    return data
  },

  /**
   * Crea una cuenta de demostracion aislada y abre sesion con ella.
   *
   * Cada visitante recibe SU PROPIA cuenta desechable, ya sembrada con datos
   * ficticios. No hay credenciales que introducir: el backend emite la cookie
   * de sesion directamente en esta respuesta.
   */
  async startDemo(): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/auth/demo')
    return data
  },

  /**
   * Devuelve el usuario de la sesion actual.
   *
   * Es la unica forma que tiene el frontend de saber si hay sesion iniciada:
   * la cookie es httpOnly y no puede inspeccionarse desde JavaScript, asi que
   * hay que preguntarselo al backend. Un 401 aqui significa simplemente
   * "visitante anonimo" y no es un error que deba mostrarse.
   */
  async getCurrentUser(): Promise<User> {
    const { data } = await api.get<User>('/auth/me')
    return data
  },

  /**
   * Cierra la sesion.
   *
   * Tiene que ejecutarlo el servidor: el frontend no puede borrar una cookie
   * httpOnly, solo el backend puede invalidarla con una cabecera Set-Cookie.
   */
  async logout(): Promise<MessageResponse> {
    const { data } = await api.post<MessageResponse>('/auth/logout')
    return data
  },
}

// ---------------------------------------------------------------------------
// Sesiones de sueno
// ---------------------------------------------------------------------------

export const sessionsService = {
  async list(limit = 100, offset = 0): Promise<SleepSession[]> {
    const { data } = await api.get<SleepSession[]>('/sessions', {
      params: { limit, offset },
    })
    return data
  },

  async getById(id: number): Promise<SleepSession> {
    const { data } = await api.get<SleepSession>(`/sessions/${id}`)
    return data
  },

  /** Crea una sesion. La respuesta ya incluye el score calculado. */
  async create(payload: SleepSessionPayload): Promise<SleepSession> {
    const { data } = await api.post<SleepSession>('/sessions', payload)
    return data
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/sessions/${id}`)
  },
}

// ---------------------------------------------------------------------------
// Habitos diarios
// ---------------------------------------------------------------------------

export const habitsService = {
  async list(limit = 100, offset = 0): Promise<DailyHabit[]> {
    const { data } = await api.get<DailyHabit[]>('/habits', {
      params: { limit, offset },
    })
    return data
  },

  /**
   * Registra o actualiza los habitos de un dia (upsert).
   *
   * Efecto secundario en el backend: recalcula el score de la sesion de sueno
   * de esa noche.
   */
  async upsert(payload: DailyHabitPayload): Promise<DailyHabit> {
    const { data } = await api.post<DailyHabit>('/habits', payload)
    return data
  },
}

// ---------------------------------------------------------------------------
// Analitica
// ---------------------------------------------------------------------------

export const analyticsService = {
  async getSummary(): Promise<AnalyticsSummary> {
    const { data } = await api.get<AnalyticsSummary>('/analytics/summary')
    return data
  },

  /** Recalcula el score de una sesion y devuelve su desglose por componente. */
  async getSessionScore(sessionId: number): Promise<SessionScore> {
    const { data } = await api.get<SessionScore>(`/analytics/score/${sessionId}`)
    return data
  },
}
