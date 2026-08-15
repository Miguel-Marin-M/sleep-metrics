import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  /** Muestra un indicador de carga y deshabilita el boton. */
  isLoading?: boolean
  children: ReactNode
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-series-1 text-white hover:bg-[#256abf] focus-visible:outline-series-1',
  secondary: 'bg-surface text-ink border border-border hover:bg-surface-sunken focus-visible:outline-series-1',
  danger: 'bg-surface text-[#a52d2d] border border-status-critical/40 hover:bg-status-critical/10 focus-visible:outline-status-critical',
  ghost: 'bg-transparent text-ink-secondary hover:bg-surface-sunken focus-visible:outline-series-1',
}

const SIZE_CLASSES: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
}

/**
 * Boton base de la aplicacion.
 *
 * Centralizar las variantes aqui es lo que mantiene la coherencia visual: si
 * cada pantalla escribiera sus propias clases de Tailwind, los botones
 * acabarian divergiendo en color, radio y espaciado.
 *
 * `focus-visible:outline` no es decorativo: es el indicador de foco para quien
 * navega con teclado. Eliminarlo dejaria la aplicacion inutilizable sin raton.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      // Un boton en carga debe estar deshabilitado: si no, un doble clic
      // enviaria el formulario dos veces.
      disabled={disabled || isLoading}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium',
        'transition-colors duration-150',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      ].join(' ')}
      {...props}
    >
      {isLoading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          // aria-hidden porque el estado de carga ya lo comunica el texto
          // visible del boton; anunciarlo dos veces sobra.
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  )
}
