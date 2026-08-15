import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description: string
  /** Accion sugerida: normalmente un enlace a la pantalla que resuelve el vacio. */
  action?: ReactNode
}

/**
 * Estado vacio de una seccion sin datos.
 *
 * Existe como componente propio porque un usuario recien registrado ve
 * exclusivamente pantallas vacias, y ese primer contacto determina si entiende
 * la aplicacion. Un panel en blanco parece una pantalla rota; un estado vacio
 * explica que falta y ofrece el siguiente paso.
 */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="max-w-md text-sm text-ink-secondary">{description}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
