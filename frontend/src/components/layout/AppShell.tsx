'use client'

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { DemoBanner } from '@/components/layout/DemoBanner'
import { Sidebar } from '@/components/layout/Sidebar'

/**
 * Estructura del area privada: barra lateral permanente en escritorio y menu
 * lateral deslizante (drawer) en movil.
 *
 * ESTRATEGIA RESPONSIVE
 * ---------------------
 * El punto de corte es `md` (768 px), el mismo que ya usaba el layout:
 *
 *   >= md   La barra lateral es un elemento fijo de 256 px pegado al viewport.
 *           El diseno de escritorio no cambia en absoluto.
 *
 *   <  md   La barra lateral desaparece del flujo y se sustituye por una
 *           cabecera fija con boton de menu. Al pulsarlo, la misma barra
 *           lateral entra deslizandose desde la izquierda sobre un fondo
 *           oscurecido.
 *
 * Se reutiliza el componente <Sidebar> en ambos casos en lugar de escribir una
 * navegacion movil aparte: dos navegaciones distintas acabarian divergiendo en
 * cuanto se anadiera una pantalla nueva a una y se olvidara en la otra.
 *
 * POR QUE EL DRAWER SE MANTIENE MONTADO
 * -------------------------------------
 * El panel esta siempre en el DOM y se oculta con `invisible`
 * (visibility: hidden) en lugar de desmontarse. Dos motivos:
 *
 *   1. La transicion de entrada necesita que el elemento exista antes de
 *      animarse; montandolo al vuelo, el primer render ya aparece en su
 *      posicion final y no hay deslizamiento.
 *   2. `visibility: hidden` saca a TODOS sus descendientes del orden de
 *      tabulacion. Con `opacity: 0` o un simple desplazamiento fuera de
 *      pantalla, los enlaces del menu cerrado seguirian siendo enfocables con
 *      el tabulador, atrapando a quien navega con teclado en un menu invisible.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const pathname = usePathname()

  // Referencias necesarias para gestionar el foco del teclado.
  const drawerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const closeMenu = useCallback(() => setIsMenuOpen(false), [])

  /**
   * Cierra el menu al navegar a otra ruta.
   *
   * Sin esto, el drawer quedaria abierto sobre la pantalla nueva. Los enlaces
   * llaman ademas a `onNavigate` para cubrir el caso en que se pulsa la ruta
   * actual, donde `pathname` no cambia y este efecto no se dispara.
   */
  useEffect(() => {
    setIsMenuOpen(false)
  }, [pathname])

  /**
   * Cierra el menu si la ventana se ensancha hasta el rango de escritorio.
   *
   * Cubre el caso de rotar el movil o redimensionar la ventana con el menu
   * abierto: sin esto, el bloqueo del scroll del body seguiria activo aunque el
   * drawer ya no fuera visible, y la pagina quedaria inmovil.
   */
  useEffect(() => {
    if (!isMenuOpen) return

    const desktopQuery = window.matchMedia('(min-width: 768px)')
    const handleChange = (event: MediaQueryListEvent) => {
      if (event.matches) setIsMenuOpen(false)
    }

    desktopQuery.addEventListener('change', handleChange)
    return () => desktopQuery.removeEventListener('change', handleChange)
  }, [isMenuOpen])

  /**
   * Comportamiento de dialogo modal mientras el menu esta abierto:
   * bloqueo del scroll de fondo, cierre con Escape y confinamiento del foco.
   *
   * El confinamiento del foco (focus trap) es lo que hace honesto el
   * `aria-modal="true"`: sin el, el tabulador saldria del menu hacia el
   * contenido de detras, que visualmente esta tapado por el fondo oscuro.
   */
  useEffect(() => {
    if (!isMenuOpen) return

    // El nodo del boton se captura AHORA, en una variable local, en lugar de
    // leer `triggerRef.current` dentro de la limpieza. Es el patron correcto
    // con refs: para cuando la limpieza se ejecuta, la ref podria apuntar ya a
    // otro nodo (o a null si el elemento se desmonto), y el foco acabaria en
    // un sitio equivocado o en ninguno.
    const trigger = triggerRef.current

    // 1. Bloqueo del scroll de fondo. Se guarda el valor previo en lugar de
    //    asumir que era "" para no pisar un estilo puesto por otro componente.
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // 2. El foco entra en el drawer, en su primer elemento interactivo.
    const focusableSelector =
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'

    const getFocusable = (): HTMLElement[] =>
      Array.from(drawerRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? [])

    getFocusable()[0]?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMenuOpen(false)
        return
      }

      if (event.key !== 'Tab') return

      const focusable = getFocusable()
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      // Ciclo circular: desde el ultimo elemento, Tab vuelve al primero; desde
      // el primero, Shift+Tab salta al ultimo.
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow

      // 3. Al cerrar, el foco vuelve al boton que abrio el menu. Sin esto
      //    quedaria en el <body> y quien navega con teclado tendria que
      //    recorrer la pagina entera desde el principio.
      trigger?.focus()
    }
  }, [isMenuOpen])

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* ================================================================
          CABECERA MOVIL (< md)
          Fija en la parte superior para que el menu este siempre accesible
          sin tener que volver arriba del todo en una pagina larga.
          ================================================================ */}
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-hairline bg-surface px-4 py-3 md:hidden">
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setIsMenuOpen(true)}
          aria-label="Abrir menu de navegacion"
          aria-expanded={isMenuOpen}
          aria-controls="menu-lateral-movil"
          className="rounded-lg p-1.5 text-ink transition-colors hover:bg-surface-sunken focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-series-1"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M3.5 6h15M3.5 11h15M3.5 16h15" />
          </svg>
        </button>

        <Link
          href="/dashboard"
          className="text-base font-semibold tracking-tight text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-series-1"
        >
          SleepMetrics
        </Link>
      </header>

      {/* ================================================================
          BARRA LATERAL DE ESCRITORIO (>= md)
          Identica al diseno anterior: 256 px, pegada al viewport y con su
          propio scroll cuando el contenido no cabe.
          ================================================================ */}
      <div className="hidden md:sticky md:top-0 md:block md:h-screen md:w-64 md:shrink-0">
        <Sidebar />
      </div>

      {/* ================================================================
          DRAWER MOVIL (< md)
          ================================================================ */}

      {/* Fondo oscurecido. Cierra el menu al pulsarlo, que es el gesto que
          cualquier usuario de movil espera.

          aria-hidden y sin rol: es un elemento decorativo cuya funcion ya
          cubren el boton de cierre y la tecla Escape, asi que anunciarlo a un
          lector de pantalla solo anadiria ruido. */}
      <div
        onClick={closeMenu}
        aria-hidden="true"
        className={[
          'fixed inset-0 z-40 bg-ink/40 transition-opacity duration-200 md:hidden',
          isMenuOpen ? 'visible opacity-100' : 'invisible opacity-0',
        ].join(' ')}
      />

      {/* Panel deslizante. */}
      <div
        ref={drawerRef}
        id="menu-lateral-movil"
        role="dialog"
        aria-modal="true"
        aria-label="Menu de navegacion"
        className={[
          'fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] shadow-xl md:hidden',
          'transition-[transform,visibility] duration-200 ease-out',
          isMenuOpen ? 'visible translate-x-0' : 'invisible -translate-x-full',
        ].join(' ')}
      >
        <Sidebar onNavigate={closeMenu} onClose={closeMenu} />
      </div>

      {/* ================================================================
          CONTENIDO
          ================================================================ */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* El aviso de demostracion va dentro de la columna de contenido y no
            sobre toda la pagina, para que en escritorio no empuje ni tape la
            barra lateral. Se renderiza solo en cuentas de demostracion. */}
        <DemoBanner />

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
