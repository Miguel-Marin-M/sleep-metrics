'use client'

import { useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { getErrorMessage } from '@/lib/api'
import { describeNight, todayAsInputValue } from '@/lib/format'
import { habitsService } from '@/lib/services'
import type { DailyHabit } from '@/types/api'

interface HabitFormProps {
  onSuccess: (habit: DailyHabit) => void
}

/** Equivalencias de referencia mostradas como ayuda al usuario. */
const CAFFEINE_HINT = 'Cafe expreso ~63 mg, taza de cafe ~95 mg, lata de refresco de cola ~35 mg.'

export function HabitForm({ onSuccess }: HabitFormProps) {
  const [date, setDate] = useState(() => todayAsInputValue())
  const [caffeineMg, setCaffeineMg] = useState('0')
  const [lastCaffeineTime, setLastCaffeineTime] = useState('')
  const [exerciseMinutes, setExerciseMinutes] = useState('0')
  const [screenTime, setScreenTime] = useState('0')

  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const caffeineValue = Number(caffeineMg)

  // Traduce la fecha elegida al tramo real que cubre, para que no quede duda
  // de que noche se esta registrando.
  const nightHint = date ? describeNight(date) : undefined

  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    if (!date) {
      errors.date = 'Indica el dia al que corresponden los hábitos.'
    } else if (date > todayAsInputValue()) {
      errors.date = 'No se pueden registrar hábitos con fecha futura.'
    }

    if (!Number.isInteger(caffeineValue) || caffeineValue < 0 || caffeineValue > 2000) {
      errors.caffeineMg = 'Introduce una cantidad entre 0 y 2000 mg.'
    }

    const exercise = Number(exerciseMinutes)
    if (!Number.isInteger(exercise) || exercise < 0 || exercise > 1440) {
      errors.exerciseMinutes = 'Introduce un valor entre 0 y 1440 minutos.'
    }

    const screen = Number(screenTime)
    if (!Number.isInteger(screen) || screen < 0 || screen > 1440) {
      errors.screenTime = 'Introduce un valor entre 0 y 1440 minutos.'
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
      const habit = await habitsService.upsert({
        date,
        caffeine_mg: caffeineValue,
        // Sin cafeina, la hora no tiene sentido y se envia null. El backend
        // aplica la misma normalizacion, pero enviarlo ya limpio evita
        // depender de ello.
        last_caffeine_time: caffeineValue > 0 && lastCaffeineTime ? lastCaffeineTime : null,
        exercise_minutes: Number(exerciseMinutes),
        screen_time_before_bed_minutes: Number(screenTime),
      })

      onSuccess(habit)
    } catch (err) {
      setError(getErrorMessage(err, 'No se han podido guardar los hábitos.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {error && <Alert variant="error">{error}</Alert>}

      <Alert variant="info">
        Si te acostaste <strong>despues de medianoche</strong>, elige el dia anterior: dormirte a
        las 00:30 del sabado es la noche del viernes. Guardar recalcula automaticamente el score
        de esa noche.
      </Alert>

      <Input
        label="Noche del"
        type="date"
        required
        max={todayAsInputValue()}
        value={date}
        onChange={(e) => setDate(e.target.value)}
        error={fieldErrors.date}
        hint={nightHint}
        disabled={isSubmitting}
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          label="Cafeina total (mg)"
          type="number"
          min={0}
          max={2000}
          step={1}
          required
          value={caffeineMg}
          onChange={(e) => setCaffeineMg(e.target.value)}
          error={fieldErrors.caffeineMg}
          hint={CAFFEINE_HINT}
          disabled={isSubmitting}
        />

        <Input
          label="Hora del ultimo cafe"
          type="time"
          value={lastCaffeineTime}
          onChange={(e) => setLastCaffeineTime(e.target.value)}
          // El campo se deshabilita si no hay cafeina: pedir la hora de un
          // consumo que no existe confundiria al usuario.
          disabled={isSubmitting || caffeineValue === 0}
          hint={
            caffeineValue === 0
              ? 'Se activa al registrar cafeina.'
              : 'Opcional, pero mejora mucho la precision del score.'
          }
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          label="Ejercicio (minutos)"
          type="number"
          min={0}
          max={1440}
          step={1}
          required
          value={exerciseMinutes}
          onChange={(e) => setExerciseMinutes(e.target.value)}
          error={fieldErrors.exerciseMinutes}
          hint="Se registra como seguimiento; no entra en el calculo del score."
          disabled={isSubmitting}
        />

        <Input
          label="Pantallas antes de dormir (minutos)"
          type="number"
          min={0}
          max={1440}
          step={1}
          required
          value={screenTime}
          onChange={(e) => setScreenTime(e.target.value)}
          error={fieldErrors.screenTime}
          hint="Uso de pantallas en la hora previa a acostarte."
          disabled={isSubmitting}
        />
      </div>

      <Button type="submit" isLoading={isSubmitting}>
        {isSubmitting ? 'Guardando...' : 'Guardar hábitos'}
      </Button>
    </form>
  )
}
