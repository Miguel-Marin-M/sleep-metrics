import type { ReactNode } from 'react'

type AlertVariant = 'error' | 'success' | 'info'

interface AlertProps {
  variant?: AlertVariant
  children: ReactNode
  className?: string
}

/**
 * Mensaje de estado (error, exito, informacion).
 *
 * Cada variante lleva un icono ademas del color. Es un requisito de
 * accesibilidad y no un adorno: el color por si solo no transmite informacion a
 * quien tiene una deficiencia en la vision del color, asi que la forma del
 * icono y el texto tienen que bastar por si mismos.
 */
const VARIANT_CONFIG: Record<AlertVariant, { classes: string; icon: string; label: string }> = {
  error: {
    classes: 'bg-status-critical/8 border-status-critical/30 text-[#a52d2d]',
    icon: '!',
    label: 'Error',
  },
  success: {
    classes: 'bg-status-good/8 border-status-good/30 text-[#0a7d0a]',
    icon: '+',
    label: 'Correcto',
  },
  info: {
    classes: 'bg-series-1/8 border-series-1/25 text-[#1c5cab]',
    icon: 'i',
    label: 'Informacion',
  },
}

export function Alert({ variant = 'info', children, className = '' }: AlertProps) {
  const config = VARIANT_CONFIG[variant]

  return (
    <div
      // role="alert" hace que los lectores de pantalla lo anuncien en cuanto
      // aparece, sin esperar a que el usuario navegue hasta el.
      role="alert"
      className={[
        'flex items-start gap-3 rounded-lg border px-4 py-3 text-sm',
        config.classes,
        className,
      ].join(' ')}
    >
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold"
        aria-hidden="true"
      >
        {config.icon}
      </span>
      <span className="sr-only">{config.label}: </span>
      <div className="flex-1">{children}</div>
    </div>
  )
}
