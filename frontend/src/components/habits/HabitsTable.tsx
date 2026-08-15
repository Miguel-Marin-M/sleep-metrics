import { EmptyState } from '@/components/ui/EmptyState'
import { formatDate } from '@/lib/format'
import type { DailyHabit } from '@/types/api'

interface HabitsTableProps {
  habits: DailyHabit[]
}

/** Recorta "22:30:00" a "22:30"; devuelve un guion si no hay hora. */
function formatShortTime(time: string | null): string {
  if (!time) return '-'
  return time.slice(0, 5)
}

/**
 * Tabla del historial de hábitos diarios.
 *
 * Igual que la tabla de sesiones, conserva su ancho mínimo y se desplaza
 * horizontalmente dentro de su propio contenedor, de modo que la página nunca
 * hace scroll lateral.
 *
 * Ese confinamiento depende de que la tarjeta contenedora lleve `min-w-0`, que
 * `Card` ya aplica por defecto: como elemento de un grid adoptaría si no el
 * min-content de esta tabla como ancho mínimo, estirando la rejilla más allá
 * del viewport en lugar de dejar que el contenedor recorte.
 *
 * Se mantiene separada de SessionsTable en lugar de generalizar ambas en un
 * componente de tabla parametrizable: las columnas, los formatos y las acciones
 * son distintos, y la abstracción prematura acabaría siendo más difícil de leer
 * que las dos tablas explícitas.
 */
export function HabitsTable({ habits }: HabitsTableProps) {
  if (habits.length === 0) {
    return (
      <EmptyState
        title="Sin hábitos registrados"
        description="Registra la cafeína, el ejercicio y el tiempo de pantalla de un día para afinar el score de esa noche."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <caption className="sr-only">
          Historial de hábitos diarios: cafeína, hora del último consumo, ejercicio y tiempo de
          pantalla antes de dormir.
        </caption>

        <thead>
          <tr className="border-b border-hairline text-left">
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Noche del
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              Cafeína
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              Último café
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              Ejercicio
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              Pantallas
            </th>
          </tr>
        </thead>

        <tbody>
          {habits.map((habit) => (
            <tr
              key={habit.id}
              className="border-b border-hairline transition-colors last:border-0 hover:bg-page"
            >
              <td className="whitespace-nowrap px-3 py-3 font-medium text-ink">
                {/* Se añade la hora para que parseLocalDateTime reciba un
                    formato completo y no dependa de cómo interprete el
                    navegador una fecha suelta. */}
                {formatDate(`${habit.date}T00:00:00`)}
              </td>

              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink-secondary">
                {habit.caffeine_mg} mg
              </td>

              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink-secondary">
                {formatShortTime(habit.last_caffeine_time)}
              </td>

              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink-secondary">
                {habit.exercise_minutes} min
              </td>

              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink-secondary">
                {habit.screen_time_before_bed_minutes} min
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
