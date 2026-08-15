'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/context/AuthContext'

/**
 * Pagina raiz: solo decide a donde enviar al visitante.
 *
 * No se resuelve con un `redirect()` de servidor porque la decision depende de
 * la cookie de sesion, que emite el dominio del backend (Render) y que por
 * tanto el servidor de Next.js (Vercel) no recibe ni puede leer. La unica forma
 * de saber si hay sesion es la sonda a /auth/me que ejecuta el contexto de
 * autenticacion en el navegador, y de ahi que esta pagina sea de cliente.
 */
export default function HomePage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    // Se espera a que termine la comprobacion: redirigir antes expulsaria al
    // login a un usuario que si tiene sesion valida.
    if (isLoading) return

    router.replace(isAuthenticated ? '/dashboard' : '/login')
  }, [isAuthenticated, isLoading, router])

  return (
    <main className="flex min-h-screen items-center justify-center">
      <Spinner label="Cargando SleepMetrics..." />
    </main>
  )
}
