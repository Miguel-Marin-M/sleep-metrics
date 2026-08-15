import type { Metadata, Viewport } from 'next'

import { AuthProvider } from '@/context/AuthContext'

import './globals.css'

/**
 * Metadatos del documento, compartidos por todas las paginas.
 *
 * Next.js los inyecta en el <head>. Las paginas individuales pueden ampliarlos
 * o sobrescribirlos exportando su propio objeto `metadata`.
 */
export const metadata: Metadata = {
  title: {
    default: 'SleepMetrics',
    // Las paginas hijas rellenan %s: "Panel | SleepMetrics".
    template: '%s | SleepMetrics',
  },
  description:
    'Plataforma de analisis de patrones de sueno: registra tus noches y tus hábitos diarios, y obten un score de calidad con metricas y correlaciones.',
  // Evita que la aplicacion aparezca en buscadores: es un proyecto de
  // demostracion con datos personales de quien la pruebe.
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#f9f9f7',
}

/**
 * Layout raiz de la aplicacion.
 *
 * Envuelve todo el arbol en el AuthProvider, de modo que cualquier componente
 * pueda consultar la sesion con `useAuth()`. Se coloca aqui y no en el layout
 * del area privada porque la pantalla de login tambien lo necesita: es quien
 * ejecuta el inicio de sesion.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
