'use client'

import { useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/context/AuthContext'
import { getErrorMessage } from '@/lib/api'

interface LoginFormProps {
  /** Se ejecuta tras un login correcto (normalmente, navegar al panel). */
  onSuccess: () => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { login } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    // Se limpia el error anterior: mantenerlo visible mientras se reintenta
    // hace creer que el nuevo intento tambien ha fallado.
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email: email.trim(), password })
      onSuccess()
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido iniciar sesion.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && <Alert variant="error">{error}</Alert>}

      <Input
        label="Email"
        type="email"
        // autoComplete permite al navegador y a los gestores de contrasenas
        // rellenar el formulario. Omitirlo empeora la experiencia sin ganar nada.
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="tu@email.com"
        disabled={isSubmitting}
      />

      <Input
        label="Contrasena"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Tu contrasena"
        disabled={isSubmitting}
      />

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        {isSubmitting ? 'Iniciando sesion...' : 'Iniciar sesion'}
      </Button>
    </form>
  )
}
