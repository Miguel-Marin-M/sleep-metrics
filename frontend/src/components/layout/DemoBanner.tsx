'use client'

import { useAuth } from '@/context/AuthContext'

/**
 * Aviso permanente cuando se navega con una cuenta de demostracion.
 *
 * Cumple dos funciones distintas y ambas importan:
 *
 *   1. HONESTIDAD CON EL VISITANTE. Los datos que ve son inventados. Sin este
 *      aviso, alguien podria tomarlos por reales, o peor, empezar a registrar
 *      sus propias noches en una cuenta que se va a borrar sola.
 *
 *   2. CONTEXTO PARA QUIEN EVALUA EL PROYECTO. Deja claro de un vistazo que la
 *      demostracion es una cuenta aislada y temporal, no una base de datos
 *      compartida por todos los visitantes.
 *
 * Se renderiza como una barra fina y en tono informativo, no como una alerta:
 * no ha ocurrido nada malo, es simplemente el estado en el que se esta.
 */
export function DemoBanner() {
  const { user } = useAuth()

  if (!user?.is_demo) return null

  return (
    <div
      // role="status" y no "alert": es informacion de contexto permanente, no
      // un aviso urgente que deba interrumpir al lector de pantalla.
      role="status"
      className="border-b border-series-1/25 bg-series-1/8 px-4 py-2.5 text-center text-xs text-[#1c5cab] sm:px-6"
    >
      <strong className="font-semibold">Cuenta de demostracion.</strong>{' '}
      Los datos son ficticios y solo tuyos: puedes crear, editar y borrar lo que quieras sin
      afectar a nadie. La cuenta se elimina automaticamente a las 24 horas.
    </div>
  )
}
