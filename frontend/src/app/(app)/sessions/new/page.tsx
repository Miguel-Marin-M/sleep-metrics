'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { PageHeader } from '@/components/layout/PageHeader'
import { SessionForm } from '@/components/sessions/SessionForm'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { formatDuration, formatScore, getScoreLabel } from '@/lib/format'
import type { SleepSession } from '@/types/api'

/**
 * Pantalla de registro de una sesion de sueno.
 *
 * Tras guardar NO se navega de inmediato: se muestra el score recien calculado
 * en la misma pantalla. Es una decision de producto deliberada: el score es la
 * recompensa por rellenar el formulario, y redirigir al instante se la
 * escamotearia al usuario.
 */
export default function NewSessionPage() {
  const router = useRouter()
  const [createdSession, setCreatedSession] = useState<SleepSession | null>(null)

  if (createdSession) {
    return (
      <>
        <PageHeader
          title="Sesion registrada"
          description="Tu noche se ha guardado y su score ya esta calculado."
        />

        <Card>
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            <Alert variant="success" className="w-full text-left">
              Se ha registrado una sesion de {formatDuration(createdSession.duration_hours)} con{' '}
              {createdSession.interruptions}{' '}
              {createdSession.interruptions === 1 ? 'interrupcion' : 'interrupciones'}.
            </Alert>

            {createdSession.score !== null && (
              <div>
                <p className="text-sm text-ink-secondary">Score de calidad</p>
                <p className="mt-1 text-5xl font-semibold tracking-tight text-ink">
                  {formatScore(createdSession.score)}
                </p>
                <p className="mt-1 text-sm font-medium text-ink">
                  {getScoreLabel(createdSession.score)}
                </p>
              </div>
            )}

            <p className="max-w-md text-sm text-ink-secondary">
              Si registras los hábitos de ese dia (cafeina, pantallas), el score se recalculara
              automaticamente incorporando esos factores.
            </p>

            <div className="mt-2 flex flex-wrap justify-center gap-3">
              <Button onClick={() => router.push('/dashboard')}>Ir al panel</Button>

              <Link href="/habits">
                <Button variant="secondary">Registrar hábitos del dia</Button>
              </Link>

              <Button variant="ghost" onClick={() => setCreatedSession(null)}>
                Registrar otra noche
              </Button>
            </div>
          </div>
        </Card>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Registrar sueño"
        description="Anota cuando te acostaste y cuando te despertaste. Calcularemos tu score de calidad al guardar."
      />

      <Card className="max-w-2xl">
        <SessionForm onSuccess={setCreatedSession} />
      </Card>
    </>
  )
}
