import type { Correlation } from '@/types/api'

interface CorrelationListProps {
  correlations: Correlation[]
}

/**
 * Fuerza de la correlacion expresada como barra.
 *
 * Se representa el VALOR ABSOLUTO del coeficiente, porque lo que la barra mide
 * es la intensidad de la relacion. El signo (si el habito mejora o empeora el
 * sueno) lo lleva el texto de interpretacion, no la longitud de la barra: una
 * barra no puede transmitir direccion sin ambiguedad.
 */
function CorrelationBar({ coefficient }: { coefficient: number }) {
  const magnitude = Math.abs(coefficient)
  const widthPercent = Math.min(100, magnitude * 100)

  // Relacion inversa (mas habito, peor sueno) en naranja; directa en aqua. La
  // direccion tambien se explica en palabras justo debajo, de modo que el color
  // refuerza pero no es el unico portador de la informacion.
  const color = coefficient < 0 ? '#eb6834' : '#1baf7a'

  return (
    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken">
      <div
        className="h-full rounded-full"
        style={{ width: `${widthPercent}%`, backgroundColor: color }}
      />
    </div>
  )
}

/**
 * Lista de correlaciones entre hábitos diarios y calidad del sueno.
 *
 * Cada entrada muestra el coeficiente numerico, una barra de intensidad y la
 * interpretacion en lenguaje natural que genera el backend. Los tres niveles
 * son intencionales: el numero para quien sepa leerlo, la barra para la
 * comparacion visual rapida entre factores, y la frase para que la metrica sea
 * util a alguien sin formacion estadistica.
 */
export function CorrelationList({ correlations }: CorrelationListProps) {
  return (
    <ul className="space-y-5">
      {correlations.map((correlation) => (
        <li key={correlation.factor}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm font-medium text-ink">{correlation.factor}</span>

            <span className="shrink-0 text-sm tabular-nums text-ink-secondary">
              {correlation.coefficient !== null
                ? correlation.coefficient.toFixed(2).replace('.', ',')
                : 'n/d'}
            </span>
          </div>

          {correlation.coefficient !== null && (
            <CorrelationBar coefficient={correlation.coefficient} />
          )}

          <p className="mt-1.5 text-xs text-ink-secondary">{correlation.interpretation}</p>

          {correlation.sample_size > 0 && (
            <p className="mt-0.5 text-xs text-ink-muted">
              Basado en {correlation.sample_size}{' '}
              {correlation.sample_size === 1 ? 'registro' : 'registros'}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
