'use client'

import { useState } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/context/AuthContext'
import { getErrorMessage } from '@/lib/api'

interface DemoButtonProps {
  /** Se ejecuta cuando la cuenta de demostracion esta lista. */
  onSuccess: () => void
}

/**
 * Acceso de un clic a una cuenta de demostracion.
 *
 * Cada pulsacion crea una cuenta desechable NUEVA e independiente, ya sembrada
 * con datos ficticios. No hay credenciales que teclear ni que publicar.
 *
 * El aislamiento por visitante es lo que hace que la demostracion sea fiable:
 * con una unica cuenta compartida, el primero que borrase el historial la
 * dejaria vacia para el siguiente, y dos personas a la vez se pisarian los
 * datos. Aqui cada uno tiene su parcela y puede crear, editar y borrar sin
 * restricciones.
 */
export function DemoButton({ onSuccess }: DemoButtonProps) {
  const { startDemo } = useAuth()

  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)

  const handleClick = async () => {
    setError(null)
    setIsStarting(true)

    try {
      await startDemo()
      onSuccess()
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido preparar la cuenta de demostracion.'))
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}

      <Button
        type="button"
        variant="secondary"
        className="w-full"
        isLoading={isStarting}
        onClick={() => void handleClick()}
      >
        {/* El texto del estado de carga es explicito sobre lo que esta pasando.
            La siembra tarda un par de segundos, y en el plan gratuito de Render
            puede sumarse un arranque en frio: un "Cargando..." generico haria
            pensar que la aplicacion se ha quedado colgada. */}
        {isStarting ? 'Preparando tu cuenta de prueba...' : 'Probar sin registrarme'}
      </Button>

      <p className="text-center text-xs text-ink-muted">
        Se crea una cuenta temporal con tres meses de datos de ejemplo. Puedes usarla como
        quieras: se elimina sola a las 24 horas.
      </p>
    </div>
  )
}
