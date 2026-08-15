'use client'

/**
 * Contexto de autenticacion.
 *
 * Es la unica fuente de verdad sobre "quien es el usuario actual" en todo el
 * frontend. Cualquier componente que necesite ese dato usa el hook `useAuth` en
 * lugar de consultar la API por su cuenta, de modo que una sola llamada a
 * /auth/me sirve a toda la aplicacion.
 *
 * POR QUE HACE FALTA ESTE CONTEXTO
 * --------------------------------
 * Con autenticacion por cookie httpOnly, el frontend NO puede saber si hay
 * sesion iniciada por si mismo: no puede leer la cookie ni decodificar el JWT.
 * La unica via es preguntarselo al backend con GET /auth/me, y ese resultado
 * hay que compartirlo con toda la aplicacion para no repetir la llamada en
 * cada pantalla.
 *
 * Nota adicional: la cookie la emite el dominio del backend (Render), no el del
 * frontend (Vercel), por lo que el middleware de Next.js tampoco puede verla.
 * Esa es la razon de que la proteccion de rutas se resuelva en el cliente, en
 * el layout del area privada, y no en un middleware de servidor.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { authService } from '@/lib/services'
import type { LoginPayload, RegisterPayload, User } from '@/types/api'

interface AuthContextValue {
  /** Usuario autenticado, o null si es un visitante anonimo. */
  user: User | null
  /**
   * true mientras se resuelve la sonda inicial de sesion. Es importante
   * distinguirlo de `user === null`: durante ese instante todavia no se sabe
   * si hay sesion, y redirigir al login sin esperar expulsaria a un usuario
   * legitimo en cada recarga de pagina.
   */
  isLoading: boolean
  isAuthenticated: boolean
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  /** Crea una cuenta de demostracion desechable y abre sesion con ella. */
  startDemo: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  /**
   * Sonda de sesion: pregunta al backend quien es el usuario actual.
   *
   * Un 401 aqui NO es un error: es la respuesta normal de un visitante sin
   * sesion. Por eso se captura en silencio y se traduce a `user = null`. El
   * interceptor de Axios tiene /auth/me en su lista de rutas exentas
   * precisamente para que esta llamada no dispare una redireccion.
   */
  const loadCurrentUser = useCallback(async () => {
    try {
      const currentUser = await authService.getCurrentUser()
      setUser(currentUser)
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Se ejecuta una unica vez al montar la aplicacion. Es lo que permite que la
  // sesion sobreviva a una recarga de pagina o a cerrar y reabrir el navegador:
  // la cookie sigue en el navegador y el backend la reconoce.
  useEffect(() => {
    void loadCurrentUser()
  }, [loadCurrentUser])

  const login = useCallback(async (payload: LoginPayload) => {
    // El backend emite la cookie httpOnly en esta respuesta. El usuario llega
    // en el cuerpo, asi que no hace falta una segunda llamada a /auth/me.
    const response = await authService.login(payload)
    setUser(response.user)
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    // El registro tambien deja la sesion iniciada, para no obligar al usuario a
    // introducir las mismas credenciales dos veces seguidas.
    const response = await authService.register(payload)
    setUser(response.user)
  }, [])

  const startDemo = useCallback(async () => {
    // El backend crea la cuenta, la siembra y emite la cookie en una sola
    // llamada, asi que el flujo es identico al de un registro normal.
    const response = await authService.startDemo()
    setUser(response.user)
  }, [])

  const logout = useCallback(async () => {
    try {
      // El borrado real de la cookie lo hace el servidor con Set-Cookie.
      await authService.logout()
    } finally {
      // El estado local se limpia SIEMPRE, incluso si la llamada falla por un
      // problema de red. Lo contrario dejaria al usuario viendo una interfaz
      // que afirma que sigue autenticado despues de pulsar "cerrar sesion".
      setUser(null)
    }
  }, [])

  // useMemo evita reconstruir el objeto de contexto en cada render, lo que
  // provocaria que todos los consumidores se re-renderizasen sin necesidad.
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      register,
      startDemo,
      logout,
    }),
    [user, isLoading, login, register, startDemo, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook de acceso al contexto de autenticacion.
 *
 * Lanza un error explicito si se usa fuera del provider. Es preferible a
 * devolver undefined en silencio: convierte un fallo de cableado de componentes
 * en un mensaje claro durante el desarrollo, en vez de en un TypeError oscuro.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (context === undefined) {
    throw new Error('useAuth debe usarse dentro de un <AuthProvider>.')
  }

  return context
}
