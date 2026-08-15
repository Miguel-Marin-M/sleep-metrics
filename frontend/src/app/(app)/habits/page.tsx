'use client'

import { useCallback, useEffect, useState } from 'react'

import { HabitForm } from '@/components/habits/HabitForm'
import { HabitsTable } from '@/components/habits/HabitsTable'
import { PageHeader } from '@/components/layout/PageHeader'
import { Alert } from '@/components/ui/Alert'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { getErrorMessage } from '@/lib/api'
import { habitsService } from '@/lib/services'
import type { DailyHabit } from '@/types/api'

export default function HabitsPage() {
  const [habits, setHabits] = useState<DailyHabit[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const loadHabits = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      setHabits(await habitsService.list())
    } catch (err) {
      setError(getErrorMessage(err, 'No se han podido cargar los hábitos.'))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadHabits()
  }, [loadHabits])

  /**
   * Integra en la lista los habitos recien guardados.
   *
   * El endpoint es un upsert, asi que el resultado puede ser una fila nueva o
   * una actualizada. Se resuelven ambos casos buscando por id: si ya existe se
   * sustituye, y si no, se inserta manteniendo el orden por fecha descendente
   * que usa el resto de la aplicacion.
   */
  const handleSuccess = useCallback((habit: DailyHabit) => {
    setSuccessMessage('hábitos guardados. El score de esa noche se ha recalculado.')

    setHabits((current) => {
      const exists = current.some((item) => item.id === habit.id)

      const updated = exists
        ? current.map((item) => (item.id === habit.id ? habit : item))
        : [...current, habit]

      return updated.sort((a, b) => b.date.localeCompare(a.date))
    })
  }, [])

  return (
    <>
      <PageHeader
        title="Hábitos diarios"
        description="La cafeina y el tiempo de pantalla antes de dormir son el 30% de tu score de calidad."
      />

      {successMessage && (
        <Alert variant="success" className="mb-4">
          {successMessage}
        </Alert>
      )}

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card title="Registrar hábitos" className="lg:col-span-3">
          <HabitForm onSuccess={handleSuccess} />
        </Card>

        <Card
          title="Historial"
          subtitle={habits.length > 0 ? `${habits.length} días registrados` : undefined}
          className="lg:col-span-2"
        >
          {isLoading ? <Spinner label="Cargando hábitos..." /> : <HabitsTable habits={habits} />}
        </Card>
      </div>
    </>
  )
}
