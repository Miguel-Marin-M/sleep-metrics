'use client'

import { useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/context/AuthContext'
import { getErrorMessage } from '@/lib/api'

interface RegisterFormProps {
  onSuccess: () => void
}

/** Longitud minima de contrasena. Debe coincidir con la validacion del backend. */
const MIN_PASSWORD_LENGTH = 8

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { register } = useAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  /**
   * Validacion en cliente.
   *
   * NO sustituye a la del backend, que sigue siendo la unica que cuenta: este
   * codigo se ejecuta en el navegador del usuario y es trivial saltarselo. Su
   * proposito es dar respuesta inmediata sin pagar el viaje de red, y cubrir
   * una regla que el backend ni siquiera conoce: la confirmacion de contrasena,
   * que es puramente de interfaz.
   */
  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    if (name.trim().length < 2) {
      errors.name = 'El nombre debe tener al menos 2 caracteres.'
    }

    if (!email.includes('@')) {
      errors.email = 'Introduce un email valido.'
    }

    if (password.length < MIN_PASSWORD_LENGTH) {
      errors.password = `La contrasena debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`
    }

    // bcrypt trunca a 72 bytes; el backend rechaza lo que exceda ese limite.
    // Se comprueba en bytes y no en caracteres porque una letra acentuada ocupa
    // 2 bytes en UTF-8.
    if (new TextEncoder().encode(password).length > 72) {
      errors.password = 'La contrasena es demasiado larga (maximo 72 bytes).'
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = 'Las contrasenas no coinciden.'
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
      await register({ name: name.trim(), email: email.trim(), password })
      onSuccess()
    } catch (err) {
      setError(getErrorMessage(err, 'No se ha podido crear la cuenta.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && <Alert variant="error">{error}</Alert>}

      <Input
        label="Nombre"
        type="text"
        autoComplete="name"
        required
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={fieldErrors.name}
        placeholder="Tu nombre"
        disabled={isSubmitting}
      />

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={fieldErrors.email}
        placeholder="tu@email.com"
        disabled={isSubmitting}
      />

      <Input
        label="Contrasena"
        type="password"
        // "new-password" hace que el gestor de contrasenas ofrezca generar una,
        // en lugar de autocompletar una existente.
        autoComplete="new-password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={fieldErrors.password}
        hint={`Minimo ${MIN_PASSWORD_LENGTH} caracteres.`}
        disabled={isSubmitting}
      />

      <Input
        label="Confirmar contrasena"
        type="password"
        autoComplete="new-password"
        required
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        error={fieldErrors.confirmPassword}
        disabled={isSubmitting}
      />

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        {isSubmitting ? 'Creando cuenta...' : 'Crear cuenta'}
      </Button>
    </form>
  )
}
