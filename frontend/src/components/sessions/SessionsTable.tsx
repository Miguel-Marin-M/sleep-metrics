'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ScoreBadge } from '@/components/sessions/ScoreBadge'
import { formatDate, formatDuration, formatTime } from '@/lib/format'
import type { SleepSession } from '@/types/api'

interface SessionsTableProps {
  sessions: SleepSession[]
  /** Callback de borrado. Recibe el id y debe resolver cuando haya terminado. */
  onDelete: (id: number) => Promise<void>
  /** Acción mostrada cuando no hay ninguna sesión. */
  emptyAction?: React.ReactNode
}

/**
 * Tabla del historial de sesiones de sueño.
 *
 * Cumple una doble función: es la pantalla de historial y, a la vez, la VISTA
 * ALTERNATIVA ACCESIBLE de la gráfica del panel. Los mismos datos que la línea
 * representa visualmente están aquí en texto, legibles por un lector de
 * pantalla y navegables con teclado.
 *
 * COMPORTAMIENTO RESPONSIVE
 * -------------------------
 * La tabla conserva su ancho mínimo y se desplaza horizontalmente dentro de su
 * propio contenedor. La página nunca hace scroll lateral: el desplazamiento
 * queda confinado aquí dentro.
 *
 * Para que eso funcione de verdad, la tarjeta que envuelve esta tabla necesita
 * `min-w-0` (ya lo trae `Card` por defecto). Sin él, la tarjeta —como elemento
 * de un grid— adopta como ancho mínimo el min-content de su contenido, es
 * decir los 720 px de esta tabla, y en lugar de recortarse estira la rejilla
 * hasta desbordar la pantalla. El `overflow-x-auto` de abajo no puede
 * impedirlo, porque la restricción la impone un ancestro y no este contenedor.
 *
 * Detalle de implementación: las columnas numéricas usan `tabular-nums` para
 * que las cifras se alineen verticalmente y las magnitudes sean comparables de
 * un vistazo recorriendo la columna.
 */
export function SessionsTable({ sessions, onDelete, emptyAction }: SessionsTableProps) {
  // Se guarda el id concreto en curso, y no un booleano: así el indicador de
  // carga aparece solo en la fila que se está borrando y no en todas.
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleDelete = async (session: SleepSession) => {
    const confirmed = window.confirm(
      `Se eliminará la sesión del ${formatDate(session.sleep_start)} y su score asociado. Esta acción no se puede deshacer.`,
    )
    if (!confirmed) return

    setDeletingId(session.id)
    try {
      await onDelete(session.id)
    } finally {
      setDeletingId(null)
    }
  }

  if (sessions.length === 0) {
    return (
      <EmptyState
        title="Sin sesiones registradas"
        description="Cuando registres una noche de sueño aparecerá aquí, junto con su score de calidad."
        action={emptyAction}
      />
    )
  }

  return (
    // overflow-x-auto mantiene la tabla usable en móvil: se desplaza dentro de
    // su contenedor en lugar de forzar el scroll horizontal de toda la página.
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <caption className="sr-only">
          Historial de sesiones de sueño con fecha, horario, duración, interrupciones y score de
          calidad.
        </caption>

        <thead>
          <tr className="border-b border-hairline text-left">
            {/* scope="col" asocia cada encabezado con su columna, para que un
                lector de pantalla anuncie "Duración: 7 h 32 min" al recorrer
                las celdas. */}
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Fecha
            </th>
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Horario
            </th>
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Duración
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              Interrupciones
            </th>
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Score
            </th>
            <th scope="col" className="px-3 py-2.5 font-medium text-ink-secondary">
              Notas
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium text-ink-secondary">
              <span className="sr-only">Acciones</span>
            </th>
          </tr>
        </thead>

        <tbody>
          {sessions.map((session) => (
            <tr
              key={session.id}
              className="border-b border-hairline transition-colors last:border-0 hover:bg-page"
            >
              <td className="whitespace-nowrap px-3 py-3 font-medium text-ink">
                {formatDate(session.sleep_start)}
              </td>

              <td className="whitespace-nowrap px-3 py-3 tabular-nums text-ink-secondary">
                {formatTime(session.sleep_start)} - {formatTime(session.sleep_end)}
              </td>

              <td className="whitespace-nowrap px-3 py-3 tabular-nums text-ink-secondary">
                {formatDuration(session.duration_hours)}
              </td>

              <td className="px-3 py-3 text-right tabular-nums text-ink-secondary">
                {session.interruptions}
              </td>

              <td className="px-3 py-3">
                <ScoreBadge score={session.score} />
              </td>

              <td className="max-w-[220px] px-3 py-3 text-ink-secondary">
                {/* `title` deja el texto completo accesible al pasar el ratón
                    cuando la celda lo trunca. */}
                <span className="line-clamp-2 block" title={session.notes ?? undefined}>
                  {session.notes || <span className="text-ink-muted">-</span>}
                </span>
              </td>

              <td className="px-3 py-3 text-right">
                <Button
                  variant="danger"
                  size="sm"
                  isLoading={deletingId === session.id}
                  onClick={() => void handleDelete(session)}
                  // El nombre accesible incluye la fecha: sin él, un lector de
                  // pantalla anunciaría una lista de botones "Eliminar"
                  // indistinguibles entre sí.
                  aria-label={`Eliminar la sesión del ${formatDate(session.sleep_start)}`}
                >
                  Eliminar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
