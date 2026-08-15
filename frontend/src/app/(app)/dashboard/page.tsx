'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'

import { CorrelationList } from '@/components/dashboard/CorrelationList'
import { ScoreHero } from '@/components/dashboard/ScoreHero'
import { SleepHoursChart } from '@/components/dashboard/SleepHoursChart'
import { StatCard } from '@/components/dashboard/StatCard'
import { PageHeader } from '@/components/layout/PageHeader'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/context/AuthContext'
import { getErrorMessage } from '@/lib/api'
import { formatHours, formatScore } from '@/lib/format'
import { analyticsService, sessionsService } from '@/lib/services'
import type { AnalyticsSummary, SleepSession } from '@/types/api'

/** Numero de noches representadas en la grafica. */
const CHART_DAYS = 7

export default function DashboardPage() {
  const { user } = useAuth()

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [sessions, setSessions] = useState<SleepSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Carga los datos del panel.
   *
   * Las dos peticiones se lanzan con Promise.all y no en secuencia: son
   * independientes, asi que ejecutarlas en paralelo reduce a la mitad el tiempo
   * de carga percibido. Importa especialmente en el free tier de Render, donde
   * la latencia de un arranque en frio es alta.
   */
  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const [summaryData, sessionsData] = await Promise.all([
        analyticsService.getSummary(),
        sessionsService.list(CHART_DAYS),
      ])

      setSummary(summaryData)
      setSessions(sessionsData)
    } catch (err) {
      setError(getErrorMessage(err, 'No se han podido cargar los datos del panel.'))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  if (isLoading) {
    return <Spinner label="Cargando tu panel..." />
  }

  if (error) {
    return (
      <>
        <PageHeader title="Panel" />
        <Alert variant="error">{error}</Alert>
        <Button variant="secondary" className="mt-4" onClick={() => void loadData()}>
          Reintentar
        </Button>
      </>
    )
  }

  // El backend devuelve el historial de mas reciente a mas antiguo, asi que la
  // ultima noche registrada es el primer elemento.
  const latestSession = sessions[0] ?? null
  const hasData = (summary?.total_sessions ?? 0) > 0

  return (
    <>
      <PageHeader
        title={`Hola, ${user?.name?.split(' ')[0] ?? ''}`}
        description="Resumen de tu descanso y de los hábitos que lo condicionan."
        action={
          <Link href="/sessions/new">
            <Button>Registrar sueño</Button>
          </Link>
        }
      />

      {!hasData ? (
        <Card>
          <EmptyState
            title="Bienvenido a SleepMetrics"
            description="Registra tu primera noche de sueño para empezar a ver tu score de calidad, la evolucion de tus horas de descanso y como te afectan la cafeina y las pantallas."
            action={
              <Link href="/sessions/new">
                <Button>Registrar mi primera noche</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Fila superior: la cifra protagonista y las metricas de apoyo. */}
          <div className="grid gap-6 lg:grid-cols-3">
            <Card title="Score de la ultima noche" className="lg:col-span-1">
              <ScoreHero
                score={latestSession?.score ?? null}
                caption={
                  summary?.average_score !== null && summary?.average_score !== undefined
                    ? `Tu media historica es ${formatScore(summary.average_score)}`
                    : 'Aun sin media historica'
                }
              />
            </Card>

            {/* min-w-0: este div es a su vez elemento del grid exterior, y sin
                anularlo su ancho mínimo sería el de su contenido, empujando la
                rejilla más allá del viewport. */}
            <div className="grid min-w-0 gap-6 sm:grid-cols-2 lg:col-span-2">
              <StatCard
                label="Media de sueño (7 dias)"
                value={formatHours(summary?.last_7_days.average_hours ?? null)}
                detail={`${summary?.last_7_days.sessions_count ?? 0} ${
                  summary?.last_7_days.sessions_count === 1 ? 'noche registrada' : 'noches registradas'
                }`}
              />

              <StatCard
                label="Media de sueño (30 dias)"
                value={formatHours(summary?.last_30_days.average_hours ?? null)}
                detail={`${summary?.last_30_days.sessions_count ?? 0} ${
                  summary?.last_30_days.sessions_count === 1 ? 'noche registrada' : 'noches registradas'
                }`}
              />

              <StatCard
                label="Mejor dia de la semana"
                value={summary?.best_weekday?.weekday_name ?? 'Sin datos'}
                detail={
                  summary?.best_weekday
                    ? `Score medio ${formatScore(summary.best_weekday.average_score)}`
                    : 'Necesitas mas registros'
                }
              />

              <StatCard
                label="Peor dia de la semana"
                value={summary?.worst_weekday?.weekday_name ?? 'Sin datos'}
                detail={
                  summary?.worst_weekday
                    ? `Score medio ${formatScore(summary.worst_weekday.average_score)}`
                    : 'Necesitas mas registros'
                }
              />
            </div>
          </div>

          {/* Grafica de evolucion. */}
          <Card
            title="Horas de sueño"
            subtitle={`Ultimas ${CHART_DAYS} noches registradas`}
            action={
              <Link href="/sessions">
                <Button variant="ghost" size="sm">
                  Ver historial
                </Button>
              </Link>
            }
          >
            <SleepHoursChart sessions={sessions} days={CHART_DAYS} />
          </Card>

          {/* Correlaciones habito-score. */}
          <Card
            title="Que influye en tu descanso"
            subtitle="Correlacion entre tus hábitos diarios y el score de sueño"
          >
            {summary && summary.correlations.length > 0 ? (
              <CorrelationList correlations={summary.correlations} />
            ) : (
              <EmptyState
                title="Sin correlaciones todavia"
                description="Registra tus hábitos diarios junto con tus sesiones de sueño para descubrir que factores te afectan."
                action={
                  <Link href="/habits">
                    <Button variant="secondary">Registrar hábitos</Button>
                  </Link>
                }
              />
            )}
          </Card>
        </div>
      )}
    </>
  )
}
