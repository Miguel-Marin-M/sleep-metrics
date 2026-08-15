'use client'

import { useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { getErrorMessage } from '@/lib/api'
import { formatDate, formatDuration, nightDateOf, nowAsInputValue } from '@/lib/format'
import { sessionsService } from '@/lib/services'
import type { SleepSession } from '@/types/api'

interface SessionFormProps {
  /** Se ejecuta con la sesion creada, incluido su score ya calculado. */
  onSuccess: (session: SleepSession) => void
}

/** Limites del dominio. Deben coincidir con la validacion del backend. */
const MIN_DURATION_HOURS = 0.5
const MAX_DURATION_HOURS = 24
const MAX_INTERRUPTIONS = 50

export function SessionForm({ onSuccess }: SessionFormProps) {
  // Valores iniciales sugeridos: acostarse hace 8 horas y despertar ahora. Es
  // el caso mas frecuente (se registra la noche al levantarse) y ahorra al
  // usuario teclear las dos fechas completas.
  const [sleepStart, setSleepStart] = useState(() => nowAsInputValue(-8))
  const [sleepEnd, setSleepEnd] = useState(() => nowAsInputValue(0))
  const [interruptions, setInterruptions] = useState('0')
  const [notes, setNotes] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  /**
   * Duracion calculada en vivo a partir de los dos campos.
   *
   * Se muestra bajo el formulario para que el usuario compruebe de un vistazo
   * que las fechas son las que queria, antes de enviar. Devuelve null si los
   * valores todavia no forman un intervalo valido.
   */
  const computeDuration = (): number | null => {
    if (!sleepStart || !sleepEnd) return null

    const start = new Date(sleepStart)
    const end = new Date(sleepEnd)

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
    if (end <= start) return null

    return (end.getTime() - start.getTime()) / (1000 * 60 * 60)
  }

  const duration = computeDuration()

  // Noche a la que pertenecera la sesion segun la hora de acostarse.
  const nightDate = nightDateOf(sleepStart)

  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    if (!sleepStart) errors.sleepStart = 'Indica cuando te acostaste.'
    if (!sleepEnd) errors.sleepEnd = 'Indica cuando te despertaste.'

    if (sleepStart && sleepEnd) {
      const hours = computeDuration()

      if (hours === null) {
        errors.sleepEnd = 'La hora de despertar debe ser posterior a la de acostarse.'
      } else if (hours < MIN_DURATION_HOURS) {
        errors.sleepEnd = 'Una sesion de sueño debe durar al menos 30 minutos.'
      } else if (hours > MAX_DURATION_HOURS) {
        errors.sleepEnd = 'Una sesion de sueño no puede durar mas de 24 horas.'
      }
    }

    const interruptionsValue = Number(interruptions)
    if (!Number.isInteger(interruptionsValue) || interruptionsValue < 0) {
      errors.interruptions = 'Introduce un numero entero de 0 o mas.'
    } else if (interruptionsValue > MAX_INTERRUPTIONS) {
      errors.interruptions = `El maximo admitido es ${MAX_INTERRUPTIONS}.`
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!validate()) return

    setIsSubmitting(true)

    try {
      const session = await sessionsService.create({
        // Los inputs datetime-local producen "2026-08-14T23:30", exactamente el
        // formato ISO sin zona horaria que espera el backend. No hay que
        // convertir nada: hacerlo con toISOString() pasaria el valor a UTC y
        // desplazaria la hora de acostarse.
        sleep_start: sleepStart,
        sleep_end: sleepEnd,
        interruptions: Number(interruptions),
        notes: notes.trim() || null,
      })

      onSuccess(session)
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido registrar la sesion.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {error && <Alert variant="error">{error}</Alert>}

      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          label="Me acoste"
          type="datetime-local"
          required
          value={sleepStart}
          onChange={(e) => setSleepStart(e.target.value)}
          error={fieldErrors.sleepStart}
          disabled={isSubmitting}
        />

        <Input
          label="Me desperte"
          type="datetime-local"
          required
          value={sleepEnd}
          onChange={(e) => setSleepEnd(e.target.value)}
          error={fieldErrors.sleepEnd}
          disabled={isSubmitting}
        />
      </div>

      {/* Confirmacion en vivo de la duracion y de la noche resultantes.
          Mostrar la noche aqui es lo que cierra el circulo con el formulario de
          habitos: el usuario ve exactamente que fecha debe elegir alli, sin
          tener que deducir la regla de la medianoche por su cuenta. */}
      {duration !== null && !fieldErrors.sleepEnd && (
        <div className="rounded-lg border border-hairline bg-surface-sunken px-4 py-3 text-sm">
          <p className="text-ink-secondary">
            Duracion registrada:{' '}
            <strong className="font-semibold text-ink">{formatDuration(duration)}</strong>
          </p>
          {nightDate && (
            <p className="mt-1 text-ink-secondary">
              Cuenta como la <strong className="font-semibold text-ink">noche del {formatDate(`${nightDate}T00:00:00`)}</strong>.
              Registra los hábitos de ese dia para afinar el score.
            </p>
          )}
        </div>
      )}

      <Input
        label="Interrupciones"
        type="number"
        min={0}
        max={MAX_INTERRUPTIONS}
        step={1}
        required
        value={interruptions}
        onChange={(e) => setInterruptions(e.target.value)}
        error={fieldErrors.interruptions}
        hint="Numero de veces que te despertaste durante la noche."
        disabled={isSubmitting}
      />

      <div className="w-full">
        <label htmlFor="session-notes" className="mb-1.5 block text-sm font-medium text-ink">
          Notas
        </label>
        <textarea
          id="session-notes"
          rows={3}
          maxLength={2000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={isSubmitting}
          placeholder="Cena tardia, ruido en la calle, habitacion calurosa..."
          className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-series-1 focus:outline-none focus:ring-2 focus:ring-series-1/40 disabled:bg-surface-sunken"
        />
        <p className="mt-1.5 text-xs text-ink-muted">
          Opcional. Contexto que te ayude a interpretar el score mas adelante.
        </p>
      </div>

      <Button type="submit" isLoading={isSubmitting}>
        {isSubmitting ? 'Guardando...' : 'Registrar sesion'}
      </Button>
    </form>
  )
}
