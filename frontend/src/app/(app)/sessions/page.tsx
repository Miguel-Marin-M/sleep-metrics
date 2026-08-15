'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'

import { PageHeader } from '@/components/layout/PageHeader'
import { SessionsTable } from '@/components/sessions/SessionsTable'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { getErrorMessage } from '@/lib/api'
import { sessionsService } from '@/lib/services'
import type { SleepSession } from '@/types/api'

export default function SessionsHistoryPage() {
  const [sessions, setSessions] = useState<SleepSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadSessions = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      setSessions(await sessionsService.list())
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido cargar el historial.'))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadSessions()
  }, [loadSessions])

  /**
   * Elimina una sesion y actualiza la lista.
   *
   * El estado local se filtra en lugar de recargar el historial completo desde
   * la API: la respuesta ya confirmo el borrado, asi que una segunda peticion
   * solo anadiria latencia y un parpadeo de la tabla.
   */
  const handleDelete = useCallback(async (id: number) => {
    try {
      await sessionsService.remove(id)
      setSessions((current) => current.filter((session) => session.id !== id))
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido eliminar la sesion.'))
    }
  }, [])

  return (
    <>
      <PageHeader
        title="Historial"
        description="Todas tus sesiones de sueño registradas, con su score de calidad."
        action={
          <Link href="/sessions/new">
            <Button>Registrar sueño</Button>
          </Link>
        }
      />

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <Card
        subtitle={
          sessions.length > 0
            ? `${sessions.length} ${sessions.length === 1 ? 'sesion registrada' : 'sesiones registradas'}`
            : undefined
        }
        title={sessions.length > 0 ? 'Sesiones' : undefined}
      >
        {isLoading ? (
          <Spinner label="Cargando historial..." />
        ) : (
          <SessionsTable
            sessions={sessions}
            onDelete={handleDelete}
            emptyAction={
              <Link href="/sessions/new">
                <Button>Registrar mi primera noche</Button>
              </Link>
            }
          />
        )}
      </Card>
    </>
  )
}
