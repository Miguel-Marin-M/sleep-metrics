interface StatCardProps {
  /** Etiqueta en frase, sin dos puntos finales. */
  label: string
  /** Valor principal ya formateado. */
  value: string
  /** Contexto bajo el valor: periodo, numero de muestras, etc. */
  detail?: string
}

/**
 * Tarjeta de metrica individual.
 *
 * Contrato de una stat tile: etiqueta, valor y detalle opcional. El valor es lo
 * unico prominente, porque es lo unico que se lee de un vistazo.
 *
 * Detalle tipografico: el valor NO usa `tabular-nums`. Esa variante da a cada
 * digito la anchura de un cero, lo que a tamano grande hace que un numero como
 * "121" se vea suelto y descuadrado. Las cifras tabulares se reservan para
 * columnas que deben alinearse verticalmente, como las de la tabla del historial.
 */
export function StatCard({ label, value, detail }: StatCardProps) {
  return (
    <div className="rounded-card border border-hairline bg-surface p-5 shadow-card">
      <p className="text-sm text-ink-secondary">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
      {detail && <p className="mt-1 text-xs text-ink-muted">{detail}</p>}
    </div>
  )
}
