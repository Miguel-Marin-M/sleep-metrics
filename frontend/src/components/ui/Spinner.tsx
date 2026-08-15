interface SpinnerProps {
  /** Texto anunciado a lectores de pantalla y mostrado bajo el indicador. */
  label?: string
  className?: string
}

/**
 * Indicador de carga a pantalla completa o de seccion.
 *
 * `role="status"` con `aria-live="polite"` hace que un lector de pantalla
 * anuncie el estado de carga sin interrumpir lo que el usuario este haciendo.
 * Un spinner puramente visual dejaria a esos usuarios sin ninguna senal de que
 * algo esta ocurriendo.
 */
export function Spinner({ label = 'Cargando...', className = '' }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={['flex flex-col items-center justify-center gap-3 py-12', className].join(' ')}
    >
      <span
        className="h-8 w-8 animate-spin rounded-full border-[3px] border-hairline border-t-series-1"
        aria-hidden="true"
      />
      <span className="text-sm text-ink-secondary">{label}</span>
    </div>
  )
}
