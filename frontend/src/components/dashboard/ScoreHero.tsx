import { formatScore, getScoreColor, getScoreLabel } from '@/lib/format'

interface ScoreHeroProps {
  /** Score a destacar, o null si aun no hay ninguna sesion registrada. */
  score: number | null
  /** Texto que situa el score: "ultima noche", "media historica"... */
  caption: string
}

/**
 * Cifra protagonista del panel: el score de calidad de sueno.
 *
 * Es la unica cifra "hero" de toda la aplicacion. Esa exclusividad es
 * deliberada: si varias cifras compiten por ser la mas grande de la pantalla,
 * ninguna destaca y el usuario no sabe donde mirar primero.
 *
 * El arco de progreso se dibuja en SVG en lugar de con una libreria de
 * graficas: es un unico valor sobre un maximo conocido, y montar un componente
 * de Recharts para eso seria mas codigo y mas peso de descarga.
 */
export function ScoreHero({ score, caption }: ScoreHeroProps) {
  // Geometria del arco: semicircunferencia de radio 70 centrada en (90, 90).
  const RADIUS = 70
  const CIRCUMFERENCE = Math.PI * RADIUS // longitud del semicirculo

  const safeScore = score ?? 0
  const progress = Math.max(0, Math.min(100, safeScore)) / 100

  // strokeDasharray dibuja el arco completo; strokeDashoffset "recorta" la
  // parte no alcanzada. Es la tecnica estandar para un medidor en SVG.
  const dashOffset = CIRCUMFERENCE * (1 - progress)

  const color = score !== null ? getScoreColor(score) : '#c3c2b7'

  return (
    <div className="flex flex-col items-center justify-center py-2">
      <svg width="180" height="104" viewBox="0 0 180 104" aria-hidden="true">
        {/* Pista de fondo: el recorrido completo del medidor. */}
        <path
          d={`M 20 90 A ${RADIUS} ${RADIUS} 0 0 1 160 90`}
          fill="none"
          stroke="#e1e0d9"
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Arco de valor. El color codifica la severidad, pero NUNCA en
            solitario: la etiqueta de texto de debajo dice lo mismo en palabras. */}
        {score !== null && (
          <path
            d={`M 20 90 A ${RADIUS} ${RADIUS} 0 0 1 160 90`}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
          />
        )}
      </svg>

      {/* La cifra se coloca superpuesta al arco con margen negativo. */}
      <div className="-mt-11 flex flex-col items-center">
        <span className="text-5xl font-semibold leading-none tracking-tight text-ink">
          {formatScore(score)}
        </span>
        <span className="mt-1 text-xs text-ink-muted">sobre 100</span>
      </div>

      {score !== null ? (
        <p className="mt-4 flex items-center gap-2 text-sm font-medium text-ink">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
          {getScoreLabel(score)}
        </p>
      ) : (
        <p className="mt-4 text-sm text-ink-muted">Sin datos</p>
      )}

      <p className="mt-1 text-xs text-ink-secondary">{caption}</p>
    </div>
  )
}
