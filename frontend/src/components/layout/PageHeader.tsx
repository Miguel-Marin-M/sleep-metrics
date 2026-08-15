import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  /** Accion principal de la pantalla, alineada a la derecha. */
  action?: ReactNode
}

/**
 * Cabecera comun a todas las pantallas del area privada.
 *
 * Garantiza que el titulo ocupe siempre la misma posicion y jerarquia
 * tipografica. Es un componente minimo, pero es exactamente el tipo de
 * repeticion que, copiada a mano en cada pagina, acaba divergiendo.
 */
export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-secondary">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  )
}
