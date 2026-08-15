import { formatScore, getScoreClasses, getScoreLabel } from '@/lib/format'

interface ScoreBadgeProps {
  score: number | null
  /** Muestra tambien la etiqueta cualitativa ("Excelente", "Mejorable"...). */
  showLabel?: boolean
}

/**
 * Distintivo compacto con el score de una sesion.
 *
 * Regla de accesibilidad que cumple por diseno: el color NUNCA viaja solo. El
 * distintivo siempre muestra la cifra, y opcionalmente la etiqueta cualitativa.
 * Un usuario que no distinga el verde del rojo sigue leyendo "88" y "Excelente".
 */
export function ScoreBadge({ score, showLabel = false }: ScoreBadgeProps) {
  if (score === null) {
    return (
      <span className="inline-flex items-center rounded-full border border-border bg-surface-sunken px-2.5 py-1 text-xs font-medium text-ink-muted">
        Sin calcular
      </span>
    )
  }

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold tabular-nums',
        getScoreClasses(score),
      ].join(' ')}
    >
      {formatScore(score)}
      {showLabel && <span className="font-medium">{getScoreLabel(score)}</span>}
    </span>
  )
}
