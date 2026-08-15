'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/context/AuthContext'

/**
 * Layout del area privada.
 *
 * La carpeta se llama `(app)` con parentesis: es un GRUPO DE RUTAS de Next.js,
 * que agrupa paginas bajo un layout comun SIN anadir un segmento a la URL. Por
 * eso la ruta es /dashboard y no /app/dashboard.
 *
 * PROTECCION DE RUTAS
 * -------------------
 * La comprobacion se hace en el cliente y no en un middleware de servidor por
 * una razon concreta: la cookie de sesion la emite el dominio del backend
 * (Render), asi que el navegador solo la envia a ese dominio. El servidor de
 * Next.js en Vercel nunca la recibe y no puede leerla, lo que deja al
 * middleware sin nada que inspeccionar. La unica fuente de verdad es la sonda
 * a /auth/me que ejecuta el contexto de autenticacion.
 *
 * Es importante entender que esto NO es la barrera de seguridad, sino una
 * comodidad de navegacion: la proteccion real la aplica el backend, que exige
 * un JWT valido en cada endpoint. Aunque alguien forzara la interfaz para
 * mostrar el panel, no obtendria ni un solo dato sin sesion valida.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    // Se espera a que la sonda termine: redirigir mientras isLoading es true
    // expulsaria a un usuario legitimo en cada recarga de pagina.
    if (isLoading) return

    if (!isAuthenticated) {
      // Se conserva la ruta actual para devolver al usuario aqui tras el login.
      router.replace(`/login?next=${encodeURIComponent(pathname)}`)
    }
  }, [isAuthenticated, isLoading, pathname, router])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Comprobando sesion..." />
      </div>
    )
  }

  // Sin sesion no se pinta nada: el efecto de arriba ya esta redirigiendo, y
  // mostrar el esqueleto del panel durante ese instante produciria un parpadeo
  // de contenido privado.
  if (!isAuthenticated) {
    return null
  }

  // La estructura visual (barra lateral en escritorio, menu deslizante en
  // movil) vive en AppShell. Este layout se queda solo con su responsabilidad
  // propia: decidir si el usuario puede ver esta seccion.
  return <AppShell>{children}</AppShell>
}
