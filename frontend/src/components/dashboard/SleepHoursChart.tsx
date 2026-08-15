'use client'

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'

import { EmptyState } from '@/components/ui/EmptyState'
import { formatAxisDate, formatDuration, formatScore } from '@/lib/format'
import type { SleepSession } from '@/types/api'

/**
 * Tokens de color de la grafica.
 *
 * Se declaran como constantes de JavaScript y no como clases de Tailwind
 * porque Recharts pinta SVG y necesita valores de color literales en sus props
 * (`stroke`, `fill`). Los valores son los mismos de la paleta declarada en
 * tailwind.config.ts, para que la grafica no se desvincule del resto de la
 * interfaz.
 */
const COLORS = {
  series: '#2a78d6', // slot 1 de la paleta categorica (azul)
  surface: '#fcfcfb', // superficie de la tarjeta: color del anillo de los puntos
  grid: '#e1e0d9', // rejilla, un paso por encima de la superficie
  axis: '#c3c2b7', // linea base del eje
  muted: '#898781', // texto de los ejes
  ink: '#0b0b0b',
  inkSecondary: '#52514e',
  optimalBand: '#1baf7a', // banda del rango optimo de sueno
} as const

/** Rango de sueno considerado optimo para un adulto, en horas. */
const OPTIMAL_MIN_HOURS = 7
const OPTIMAL_MAX_HOURS = 9

interface ChartPoint {
  label: string
  hours: number
  score: number | null
  fullDate: string
}

interface SleepHoursChartProps {
  sessions: SleepSession[]
  /** Numero de noches a representar. */
  days?: number
}

/**
 * Contenido del tooltip.
 *
 * Se personaliza en lugar de usar el de Recharts por dos motivos: el de serie
 * mostraria el valor crudo ("7.53") en vez de una duracion legible, y aqui se
 * puede anadir el score de esa noche, que es el dato que da sentido a la altura
 * del punto.
 *
 * El tipo es `TooltipContentProps` y no `TooltipProps`: en Recharts 3 son dos
 * cosas distintas. `TooltipProps` describe las props del componente <Tooltip>
 * (que no incluye `payload`, porque lo resuelve internamente), mientras que
 * `TooltipContentProps` describe lo que recibe el renderizador de contenido, ya
 * con el payload de los puntos activos.
 *
 * Se usan los parametros genericos POR DEFECTO en lugar de estrecharlos a
 * <number, string>. El motivo es de varianza: el <Tooltip> del arbol se declara
 * sin genericos, asi que espera un `content` capaz de aceptar el tipo ancho; una
 * funcion que solo acepta el tipo estrecho no es sustituible por el, y
 * TypeScript la rechaza. El valor concreto se recupera igualmente mas abajo con
 * la conversion a ChartPoint.
 */
function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null

  const point = payload[0].payload as ChartPoint

  return (
    <div className="rounded-lg border border-hairline bg-surface px-3 py-2 shadow-card">
      <p className="text-xs font-medium text-ink-secondary">{point.fullDate}</p>

      <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink">
        {/* El punto de color aporta la identidad de la serie; el texto se
            mantiene en tinta neutra, nunca en el color del dato. */}
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: COLORS.series }}
          aria-hidden="true"
        />
        {formatDuration(point.hours)}
      </p>

      {point.score !== null && (
        <p className="mt-0.5 text-xs text-ink-secondary">Score: {formatScore(point.score)} / 100</p>
      )}
    </div>
  )
}

/**
 * Grafica de lineas con las horas dormidas de las ultimas noches.
 *
 * Decisiones de diseno:
 *
 *   - UNA SOLA SERIE, por tanto SIN leyenda: con un unico color, el titulo de
 *     la tarjeta ya dice que se esta representando y una caja de leyenda con un
 *     solo elemento solo repetiria el titulo ocupando espacio.
 *
 *   - Banda del rango optimo (7-9 h) en verde muy tenue. Es lo que convierte la
 *     grafica en interpretable de un vistazo: sin ella, el usuario ve una linea
 *     que sube y baja pero no sabe donde deberia estar.
 *
 *   - Rejilla solo horizontal y en hairline. Las lineas verticales no aportan
 *     nada aqui (el eje X es categorico) y anaden ruido.
 *
 *   - Etiquetas SELECTIVAS: el valor no se escribe sobre cada punto. Los
 *     valores puntuales los sirve el tooltip, y la tabla del historial actua
 *     como vista alternativa accesible del mismo conjunto de datos.
 */
export function SleepHoursChart({ sessions, days = 7 }: SleepHoursChartProps) {
  // El backend devuelve el historial de mas reciente a mas antiguo. La grafica
  // necesita el orden inverso: el tiempo avanza hacia la derecha.
  const data: ChartPoint[] = sessions
    .slice(0, days)
    .reverse()
    .map((session) => ({
      label: formatAxisDate(session.sleep_start),
      hours: Number(session.duration_hours.toFixed(2)),
      score: session.score,
      fullDate: formatAxisDate(session.sleep_start),
    }))

  if (data.length === 0) {
    return (
      <EmptyState
        title="Todavia no hay datos"
        description="Registra tu primera noche de sueño para ver aqui la evolucion de tus horas de descanso."
      />
    )
  }

  // Techo del eje Y redondeado hacia arriba, con un minimo de 10 h para que la
  // banda optima (7-9 h) siempre quede visible aunque el usuario haya dormido
  // poco todas las noches.
  const maxHours = Math.max(10, Math.ceil(Math.max(...data.map((point) => point.hours)) + 1))

  return (
    <div className="w-full">
      <div
        className="h-72 w-full"
        // La grafica es una imagen para tecnologias asistivas: se le da un
        // nombre y una descripcion, y se remite a la tabla del historial como
        // vista alternativa con los mismos datos en formato accesible.
        role="img"
        aria-label={`Horas de sueño de las ultimas ${data.length} noches. Los valores exactos estan disponibles en la tabla del historial.`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: -12 }}>
            {/* Banda del rango optimo, por DEBAJO de la rejilla y la linea para
                que no compita con los datos. */}
            <ReferenceArea
              y1={OPTIMAL_MIN_HOURS}
              y2={OPTIMAL_MAX_HOURS}
              fill={COLORS.optimalBand}
              fillOpacity={0.08}
              // Sin borde: es contexto de fondo, no un dato mas.
              stroke="none"
            />

            <CartesianGrid
              // Solo horizontales: las verticales sobre un eje categorico son
              // ruido puro.
              vertical={false}
              stroke={COLORS.grid}
              strokeWidth={1}
            />

            <XAxis
              dataKey="label"
              stroke={COLORS.axis}
              tick={{ fill: COLORS.muted, fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: COLORS.axis }}
            />

            <YAxis
              domain={[0, maxHours]}
              // Marcas en numeros redondos cada 2 horas: legibles y suficientes.
              ticks={Array.from({ length: Math.floor(maxHours / 2) + 1 }, (_, i) => i * 2)}
              stroke={COLORS.axis}
              tick={{ fill: COLORS.muted, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value: number) => `${value}h`}
              width={48}
            />

            <Tooltip
              // Se pasa la FUNCION y no un elemento (<ChartTooltip />): es la
              // forma que espera la firma de `content` en Recharts 3, y evita
              // tener que declarar todas las props como opcionales solo para
              // satisfacer al comprobador de tipos.
              content={ChartTooltip}
              // Linea vertical de referencia al pasar el raton: ancla la lectura
              // del tooltip al punto correcto del eje X.
              cursor={{ stroke: COLORS.grid, strokeWidth: 1 }}
            />

            <Line
              type="monotone"
              dataKey="hours"
              stroke={COLORS.series}
              // 2px con uniones redondeadas, segun la especificacion de marcas.
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              // Puntos de 8px de diametro (r=4) con anillo de 2px del color de
              // la superficie: es lo que los mantiene legibles al cruzarse con
              // la linea o entre ellos.
              dot={{
                r: 4,
                fill: COLORS.series,
                stroke: COLORS.surface,
                strokeWidth: 2,
              }}
              // El punto activo crece para ser un objetivo de raton comodo.
              activeDot={{
                r: 6,
                fill: COLORS.series,
                stroke: COLORS.surface,
                strokeWidth: 2,
              }}
              // Desactivar la animacion al actualizar evita que la linea
              // "salte" cada vez que se refrescan los datos.
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Clave de la banda de referencia. No es una leyenda de series (hay una
          sola), sino la explicacion del elemento de contexto. */}
      <p className="mt-3 flex items-center gap-2 text-xs text-ink-muted">
        <span
          className="inline-block h-2.5 w-4 rounded-sm"
          style={{ backgroundColor: COLORS.optimalBand, opacity: 0.25 }}
          aria-hidden="true"
        />
        Rango optimo de sueño para un adulto: {OPTIMAL_MIN_HOURS}-{OPTIMAL_MAX_HOURS} horas
      </p>
    </div>
  )
}
