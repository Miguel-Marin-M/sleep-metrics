import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  /** Texto secundario bajo el titulo. */
  subtitle?: string
  /** Contenido alineado a la derecha de la cabecera (acciones, filtros). */
  action?: ReactNode
  children: ReactNode
  className?: string
}

/**
 * Contenedor base de las secciones de contenido.
 *
 * La elevacion se consigue con contraste de superficie (`surface` sobre `page`)
 * y una sombra muy sutil, no con sombras marcadas: en un panel de datos, la
 * jerarquia visual debe venir del propio contenido y no del cromado.
 */
export function Card({ title, subtitle, action, children, className = '' }: CardProps) {
  return (
    <section
      className={[
        'rounded-card border border-hairline bg-surface shadow-card',
        // min-w-0 es OBLIGATORIO y no cosmético.
        //
        // Las tarjetas se usan casi siempre como elementos de un grid o un
        // flex, y esos elementos tienen `min-width: auto`, que resuelve a su
        // ancho MIN-CONTENT. Basta con que dentro haya una tabla ancha o una
        // gráfica para que la tarjeta exija ese ancho mínimo, estire la
        // columna del grid y desborde la página entera horizontalmente.
        //
        // Un `overflow-x-auto` en un div interior no lo evita: la restricción
        // la impone la tarjeta como elemento del grid, no su contenido.
        // `min-w-0` la anula y permite que el contenedor interno recorte y
        // haga scroll como corresponde.
        'min-w-0',
        className,
      ].join(' ')}
    >
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-hairline px-5 py-4">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-ink-secondary">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}

      <div className="p-5">{children}</div>
    </section>
  )
}
