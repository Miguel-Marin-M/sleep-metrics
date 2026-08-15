'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { DemoButton } from '@/components/auth/DemoButton'
import { LoginForm } from '@/components/auth/LoginForm'
import { RegisterForm } from '@/components/auth/RegisterForm'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/context/AuthContext'

type AuthMode = 'login' | 'register'

/**
 * Pantalla de acceso: login y registro en una sola ruta con conmutador.
 *
 * Un unico punto de entrada evita la friccion de "no tengo cuenta, ¿donde me
 * registro?" y mantiene el estado de la aplicacion mas simple que con dos rutas
 * separadas que hay que mantener sincronizadas.
 */
function AuthPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isAuthenticated, isLoading } = useAuth()

  const [mode, setMode] = useState<AuthMode>('login')

  /**
   * Destino tras autenticarse.
   *
   * El interceptor de Axios anade `?next=` con la ruta que el usuario intentaba
   * ver cuando caduco su sesion, para devolverlo exactamente alli.
   *
   * Se valida que empiece por "/" antes de usarlo: aceptar una URL absoluta
   * abriria una vulnerabilidad de redireccion abierta, en la que un enlace del
   * tipo `/login?next=https://sitio-malicioso.com` llevaria al usuario fuera de
   * la aplicacion tras iniciar sesion, aparentando ser parte del flujo legitimo.
   */
  const rawNext = searchParams.get('next')
  const redirectTo = rawNext && rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '/dashboard'

  // Un usuario con sesion activa no debe ver la pantalla de login.
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(redirectTo)
    }
  }, [isAuthenticated, isLoading, redirectTo, router])

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Spinner label="Comprobando sesion..." />
      </main>
    )
  }

  const handleSuccess = () => router.replace(redirectTo)

  return (
    <main className="flex min-h-screen items-center justify-center bg-page px-4 py-12">
      <div className="w-full max-w-md">
        {/* Marca */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">SleepMetrics</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Analiza tus patrones de sueño y descubre que hábitos los condicionan.
          </p>
        </div>

        <div className="rounded-card border border-hairline bg-surface p-6 shadow-card">
          {/* Conmutador entre iniciar sesion y crear cuenta.
              role="tablist" comunica a las tecnologias asistivas que son dos
              vistas alternativas del mismo panel, no dos botones sueltos. */}
          <div
            role="tablist"
            aria-label="Iniciar sesion o crear cuenta"
            className="mb-6 grid grid-cols-2 gap-1 rounded-lg bg-surface-sunken p-1"
          >
            {(['login', 'register'] as const).map((tab) => (
              <button
                key={tab}
                role="tab"
                type="button"
                aria-selected={mode === tab}
                onClick={() => setMode(tab)}
                className={[
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-series-1',
                  mode === tab
                    ? 'bg-surface text-ink shadow-sm'
                    : 'text-ink-secondary hover:text-ink',
                ].join(' ')}
              >
                {tab === 'login' ? 'Iniciar sesion' : 'Crear cuenta'}
              </button>
            ))}
          </div>

          {mode === 'login' ? (
            <LoginForm onSuccess={handleSuccess} />
          ) : (
            <RegisterForm onSuccess={handleSuccess} />
          )}

          {/* Separador entre el acceso con cuenta propia y la demostracion.
              La linea con etiqueta central deja claro que son dos caminos
              alternativos, no dos pasos del mismo formulario. */}
          <div className="my-6 flex items-center gap-3" aria-hidden="true">
            <span className="h-px flex-1 bg-hairline" />
            <span className="text-xs uppercase tracking-wide text-ink-muted">o</span>
            <span className="h-px flex-1 bg-hairline" />
          </div>

          <DemoButton onSuccess={handleSuccess} />
        </div>

        <p className="mt-6 text-center text-xs text-ink-muted">
          Tu contrasena se almacena cifrada con bcrypt y la sesion viaja en una cookie httpOnly.
        </p>
      </div>
    </main>
  )
}

/**
 * `useSearchParams` obliga a envolver el componente en <Suspense>: sin el, la
 * build de produccion de Next.js falla al intentar prerenderizar la pagina de
 * forma estatica.
 */
export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center">
          <Spinner />
        </main>
      }
    >
      <AuthPageContent />
    </Suspense>
  )
}
