import { useId, type InputHTMLAttributes, type ReactNode } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  /** Mensaje de error de validacion mostrado bajo el campo. */
  error?: string
  /** Texto de ayuda mostrado cuando no hay error. */
  hint?: ReactNode
}

/**
 * Campo de formulario con etiqueta, ayuda y error.
 *
 * El componente resuelve el cableado de accesibilidad que es facil olvidar
 * campo por campo:
 *   - `useId` genera un id unico y estable, de modo que la etiqueta quede
 *     asociada a su input (pulsar la etiqueta enfoca el campo).
 *   - `aria-invalid` y `aria-describedby` hacen que un lector de pantalla
 *     anuncie el error junto al campo en lugar de dejarlo como texto suelto.
 *   - `role="alert"` en el mensaje provoca que se anuncie en cuanto aparece.
 */
export function Input({ label, error, hint, className = '', id, ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const errorId = `${inputId}-error`
  const hintId = `${inputId}-hint`

  return (
    // min-w-0 junto a w-full: los campos `datetime-local`, `date` y `time`
    // tienen un ancho intrínseco considerable (el navegador reserva sitio para
    // el widget completo del calendario o el reloj). Usados dentro de un grid,
    // ese ancho se convierte en el mínimo del elemento y desborda en pantallas
    // estrechas. `min-w-0` deja que el campo se encoja con su contenedor.
    <div className="w-full min-w-0">
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
        {props.required && (
          <span className="ml-1 text-status-critical" aria-hidden="true">
            *
          </span>
        )}
      </label>

      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        className={[
          'w-full rounded-lg border bg-surface px-3 py-2.5 text-sm text-ink',
          'placeholder:text-ink-muted',
          'focus:outline-none focus:ring-2 focus:ring-series-1/40 focus:border-series-1',
          'disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-ink-muted',
          error ? 'border-status-critical' : 'border-border',
          className,
        ].join(' ')}
        {...props}
      />

      {error ? (
        <p id={errorId} role="alert" className="mt-1.5 text-sm text-[#a52d2d]">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="mt-1.5 text-xs text-ink-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
