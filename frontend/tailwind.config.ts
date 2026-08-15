import type { Config } from 'tailwindcss'

/**
 * Configuracion de Tailwind CSS.
 *
 * La paleta no se define con los colores por defecto de Tailwind sino con
 * TOKENS SEMANTICOS (surface, ink, series, status...). El motivo es que un
 * nombre como `bg-slate-100` describe un color, mientras que `bg-surface`
 * describe un papel dentro del sistema visual: si algun dia cambia el color,
 * cambia en un unico sitio y ninguna clase de los componentes se queda mintiendo.
 *
 * Los valores provienen de una paleta validada para accesibilidad: los colores
 * de estado (status) cumplen contraste sobre la superficie clara y, ademas,
 * NUNCA se usan solos para transmitir informacion, siempre acompanados de una
 * etiqueta de texto.
 */
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // -- Superficies -----------------------------------------------------
        // `page` es el plano de fondo; `surface` es el de las tarjetas, un paso
        // por encima. Esa minima diferencia es la que hace que una tarjeta se
        // lea como elemento elevado sin necesidad de sombras pesadas.
        page: '#f9f9f7',
        surface: '#fcfcfb',
        'surface-sunken': '#f0efec',

        // -- Tinta (texto) ---------------------------------------------------
        ink: {
          DEFAULT: '#0b0b0b', // texto principal
          secondary: '#52514e', // texto de apoyo
          muted: '#898781', // ejes, etiquetas menores
        },

        // -- Lineas ----------------------------------------------------------
        hairline: '#e1e0d9', // rejilla de graficas, separadores
        border: '#c3c2b7', // bordes de controles, eje base

        // -- Series de datos -------------------------------------------------
        // Slot 1 de la paleta categorica. La aplicacion grafica una unica serie
        // (horas de sueno), asi que con un color basta; los slots siguientes
        // quedan documentados para cuando se anadan mas series.
        series: {
          1: '#2a78d6', // azul
          2: '#eb6834', // naranja
          3: '#1baf7a', // aqua
        },

        // -- Estado ----------------------------------------------------------
        // Reservados para calidad del sueno. Nunca se reutilizan como color de
        // serie, y siempre van acompanados de texto.
        status: {
          good: '#0ca30c',
          warning: '#fab219',
          serious: '#ec835a',
          critical: '#d03b3b',
        },
      },

      fontFamily: {
        // Sans del sistema en toda la interfaz, incluidas las cifras grandes.
        // Sin fuentes decorativas: no hay que descargarlas y evita el parpadeo
        // de texto sin estilar en la primera carga.
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },

      borderRadius: {
        card: '0.75rem',
      },

      boxShadow: {
        // Sombra deliberadamente sutil: la separacion entre planos la hace el
        // contraste de superficies, no la sombra.
        card: '0 1px 2px rgba(11, 11, 11, 0.04), 0 1px 3px rgba(11, 11, 11, 0.06)',
      },
    },
  },
  plugins: [],
}

export default config
