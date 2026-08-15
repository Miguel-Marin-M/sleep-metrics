/**
 * Cliente HTTP compartido por toda la aplicacion.
 *
 * Centralizar Axios aqui (en lugar de llamar a `axios.get` suelto desde cada
 * componente) permite resolver en un unico punto tres cosas que de otro modo
 * habria que repetir en cada llamada: el envio de la cookie de sesion, la
 * reaccion a un 401 y la normalizacion de los mensajes de error.
 */

import axios, { AxiosError, type AxiosInstance } from 'axios'

import type { ApiErrorBody } from '@/types/api'

/**
 * URL base de la API.
 *
 * Se lee de una variable NEXT_PUBLIC_ porque este codigo se ejecuta en el
 * navegador. El valor de respaldo apunta al backend local para que un `npm run
 * dev` recien clonado funcione sin configuracion previa.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

/** Ruta a la que se redirige cuando la sesion deja de ser valida. */
const LOGIN_PATH = '/login'

/**
 * Rutas que NO deben provocar una redireccion automatica al recibir un 401.
 *
 * `/auth/me` es la sonda que ejecuta el contexto de autenticacion al arrancar
 * para averiguar si hay sesion: un 401 ahi es la respuesta NORMAL de un
 * visitante anonimo, no un error. `/auth/login` devuelve 401 cuando las
 * credenciales son incorrectas, y en ese caso el formulario debe mostrar el
 * mensaje, no recargar la pagina y perderlo.
 */
const SILENT_401_PATHS = ['/auth/me', '/auth/login', '/auth/register']

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,

  /**
   * withCredentials es la pieza CLAVE de la autenticacion de este proyecto.
   *
   * La sesion vive en una cookie httpOnly emitida por el backend. Por defecto,
   * el navegador NO adjunta cookies en peticiones cross-origin, y frontend
   * (Vercel) y backend (Render) estan en dominios distintos. Con esta opcion
   * activada, y con `allow_credentials=True` en el CORS del backend, el
   * navegador adjunta la cookie de forma automatica en cada peticion.
   */
  withCredentials: true,

  headers: {
    'Content-Type': 'application/json',
  },

  // Corta la peticion tras 30 s. Es un valor alto a proposito: el free tier de
  // Render suspende el servicio tras 15 minutos sin trafico, y el arranque en
  // frio puede tardar cerca de 50 segundos. Un timeout corto convertiria ese
  // primer acceso en un error en lugar de en una espera.
  timeout: 30000,
})

/**
 * INTERCEPTOR DE PETICION
 *
 * Nota importante sobre el diseno: en una autenticacion basada en localStorage,
 * aqui se leeria el token y se anadiria la cabecera `Authorization: Bearer`.
 * Este proyecto usa cookies httpOnly, de modo que el JavaScript NO PUEDE leer
 * el token (que es justamente lo que lo protege frente a XSS) y quien adjunta
 * la credencial es el propio navegador gracias a `withCredentials`.
 *
 * El interceptor sigue siendo util para lo que si es responsabilidad del
 * cliente: garantizar que las peticiones con cuerpo declaren el Content-Type
 * correcto. Ademas de ser correcto, tiene un efecto de seguridad concreto:
 * `application/json` obliga al navegador a lanzar un preflight CORS, que es lo
 * que impide que un formulario HTML de un sitio malicioso ejecute una peticion
 * con la cookie de sesion adjunta (CSRF).
 */
api.interceptors.request.use(
  (config) => {
    const method = config.method?.toUpperCase()

    if (method && ['POST', 'PUT', 'PATCH'].includes(method)) {
      config.headers['Content-Type'] = 'application/json'
    }

    return config
  },
  (error) => Promise.reject(error),
)

/**
 * INTERCEPTOR DE RESPUESTA
 *
 * Concentra el manejo de la sesion expirada. Sin el, cada componente tendria
 * que comprobar por su cuenta si el error era un 401 y decidir que hacer, y
 * bastaria con que uno lo olvidara para dejar al usuario ante una pantalla rota
 * en lugar de devolverlo al login.
 */
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    const status = error.response?.status
    const url = error.config?.url ?? ''

    const isSilentPath = SILENT_401_PATHS.some((path) => url.startsWith(path))

    if (status === 401 && !isSilentPath && typeof window !== 'undefined') {
      // La sesion expiro o la cookie ya no es valida. Se redirige al login
      // conservando la ruta actual para poder volver a ella tras autenticarse.
      //
      // Se usa window.location y no el router de Next a proposito: este modulo
      // no es un componente de React y no puede usar hooks. Ademas, una recarga
      // completa limpia cualquier estado obsoleto que quedara en memoria.
      const currentPath = window.location.pathname + window.location.search

      if (!window.location.pathname.startsWith(LOGIN_PATH)) {
        const redirectTo = encodeURIComponent(currentPath)
        window.location.href = `${LOGIN_PATH}?next=${redirectTo}`
      }
    }

    return Promise.reject(error)
  },
)

/**
 * Traduce cualquier error de Axios a un mensaje legible para el usuario.
 *
 * Es necesario porque los fallos llegan en formatos muy distintos: FastAPI
 * devuelve `detail` como cadena en los errores de negocio pero como array de
 * objetos en los de validacion (422), y un fallo de red no trae respuesta
 * alguna. Sin esta normalizacion, la interfaz acabaria mostrando
 * "[object Object]" o un "Network Error" sin contexto.
 */
export function getErrorMessage(error: unknown, fallback = 'Ha ocurrido un error inesperado.'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback
  }

  const axiosError = error as AxiosError<ApiErrorBody>

  // Sin respuesta: la peticion no llego a completarse.
  if (!axiosError.response) {
    if (axiosError.code === 'ECONNABORTED') {
      return 'La peticion ha tardado demasiado. Es posible que el servidor este arrancando; intentalo de nuevo en unos segundos.'
    }
    return 'No se ha podido conectar con el servidor. Comprueba tu conexion e intentalo de nuevo.'
  }

  const detail = axiosError.response.data?.detail

  if (typeof detail === 'string') {
    return detail
  }

  // Error de validacion de Pydantic: se construye un mensaje por campo.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        // `loc` es del tipo ["body", "email"]; el ultimo elemento es el campo.
        const field = item.loc?.[item.loc.length - 1]
        return field && field !== 'body' ? `${field}: ${item.msg}` : item.msg
      })
      .join('. ')
  }

  // Codigos de estado sin cuerpo util.
  switch (axiosError.response.status) {
    case 401:
      return 'Tu sesion ha caducado. Vuelve a iniciar sesion.'
    case 403:
      return 'No tienes permiso para realizar esta accion.'
    case 404:
      return 'No se ha encontrado el recurso solicitado.'
    case 409:
      return 'La operacion entra en conflicto con datos ya existentes.'
    case 500:
      return 'Error interno del servidor. Intentalo de nuevo mas tarde.'
    default:
      return fallback
  }
}
