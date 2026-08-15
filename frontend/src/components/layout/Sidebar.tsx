'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/Button'

/**
 * Definicion de la navegacion.
 *
 * Se declara como datos y no como JSX repetido: anadir una pantalla es anadir
 * una entrada a este array, sin tocar el marcado ni la logica de resaltado.
 */
const NAV_ITEMS = [
  { href: '/dashboard', label: 'Panel', description: 'Resumen y tendencias' },
  { href: '/sessions/new', label: 'Registrar sueño', description: 'Nueva sesion' },
  { href: '/sessions', label: 'Historial', description: 'Sesiones anteriores' },
  { href: '/habits', label: 'Hábitos', description: 'Cafeina, pantallas, ejercicio' },
] as const

interface SidebarProps {
  /**
   * Se ejecuta al pulsar cualquier enlace de navegacion.
   *
   * Lo usa el drawer movil para cerrarse. No basta con reaccionar al cambio de
   * ruta: si el usuario pulsa el enlace de la pantalla en la que ya esta, la
   * ruta no cambia y el menu se quedaria abierto.
   */
  onNavigate?: () => void

  /**
   * Cuando se proporciona, se renderiza un boton de cierre en la cabecera.
   *
   * Solo lo pasa el drawer movil: la barra lateral de escritorio es permanente
   * y no se cierra, asi que alli este boton no tendria sentido.
   */
  onClose?: () => void
}

export function Sidebar({ onNavigate, onClose }: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  /**
   * Determina si una entrada de navegacion esta activa.
   *
   * El caso de /sessions requiere cuidado: una coincidencia por prefijo
   * marcaria "Historial" como activo tambien estando en /sessions/new. Se
   * exige coincidencia exacta para esa ruta y se admite el prefijo para el
   * resto (asi /sessions/42 seguiria resaltando "Historial" si se anadiera esa
   * pantalla de detalle).
   */
  const isActive = (href: string): boolean => {
    if (href === '/sessions') {
      return pathname === '/sessions' || /^\/sessions\/\d+$/.test(pathname)
    }
    return pathname === href || pathname.startsWith(`${href}/`)
  }

  return (
    // h-full w-full: el tamano lo decide el contenedor (64 en escritorio, 72 en
    // el drawer). Asi el mismo componente sirve a los dos usos sin duplicarse.
    <aside className="flex h-full w-full flex-col border-r border-hairline bg-surface">
      {/* Marca */}
      <div className="flex items-start justify-between gap-2 border-b border-hairline px-5 py-5">
        <Link href="/dashboard" className="block" onClick={onNavigate}>
          <span className="text-lg font-semibold tracking-tight text-ink">SleepMetrics</span>
          <span className="mt-0.5 block text-xs text-ink-muted">Analisis de patrones de sueño</span>
        </Link>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar menu"
            className="-mr-1 shrink-0 rounded-lg p-1.5 text-ink-secondary transition-colors hover:bg-surface-sunken hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-series-1"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        )}
      </div>

      {/* Navegacion */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Navegacion principal">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href)

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              // aria-current identifica la pagina actual para lectores de
              // pantalla. Sin el, la unica senal seria el color de fondo, que
              // no es perceptible por esos usuarios.
              aria-current={active ? 'page' : undefined}
              className={[
                'block rounded-lg px-3 py-2.5 transition-colors',
                'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-series-1',
                active
                  ? 'bg-series-1/10 text-[#1c5cab]'
                  : 'text-ink-secondary hover:bg-surface-sunken hover:text-ink',
              ].join(' ')}
            >
              <span className="block text-sm font-medium">{item.label}</span>
              <span className="block text-xs text-ink-muted">{item.description}</span>
            </Link>
          )
        })}
      </nav>

      {/* Usuario y cierre de sesion */}
      <div className="border-t border-hairline px-5 py-4">
        <p className="truncate text-sm font-medium text-ink" title={user?.name}>
          {user?.name}
        </p>
        <p className="mb-3 truncate text-xs text-ink-muted" title={user?.email}>
          {user?.email}
        </p>
        <Button variant="secondary" size="sm" className="w-full" onClick={() => void logout()}>
          Cerrar sesion
        </Button>
      </div>
    </aside>
  )
}
