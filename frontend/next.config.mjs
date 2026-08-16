/**
 * Origen real del backend, al que apunta el proxy.
 *
 * Es una variable de SERVIDOR, sin el prefijo NEXT_PUBLIC_: la usa unicamente
 * el proxy de Next.js, nunca el codigo que corre en el navegador. Esa es
 * justamente la idea del montaje: que el navegador no llegue a saber que
 * existe un segundo dominio.
 */
const BACKEND_ORIGIN = (process.env.BACKEND_ORIGIN ?? 'http://localhost:8000').replace(/\/$/, '')

/**
 * Configuracion de Next.js para SleepMetrics.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  // Detecta patrones problematicos de React durante el desarrollo (efectos que
  // no se limpian, estado mutado). Se desactiva solo en la build de produccion.
  reactStrictMode: true,

  // Elimina la cabecera "X-Powered-By: Next.js", que revela el framework y su
  // version sin aportar nada al usuario.
  poweredByHeader: false,

  /**
   * PROXY HACIA EL BACKEND
   *
   * Todas las llamadas a la API salen del navegador hacia `/api/...`, es decir
   * hacia el MISMO origen que sirve la aplicacion, y Next.js las reenvia por
   * detras al backend. El navegador nunca contacta con Render directamente.
   *
   * POR QUE ES NECESARIO
   * --------------------
   * La sesion vive en una cookie httpOnly. En el despliegue, frontend y backend
   * estan en dominios distintos (`*.vercel.app` y `*.onrender.com`), y ambos
   * figuran en la Public Suffix List, de modo que para el navegador son sitios
   * incuestionablemente distintos: la cookie era de TERCEROS.
   *
   * Con `SameSite=None; Secure` eso deberia bastar segun la especificacion,
   * pero los navegadores llevan anos restringiendo las cookies de terceros:
   * Safari las bloquea por defecto y Chrome tambien en incognito y cada vez mas
   * fuera de el. El resultado observado era exactamente ese: la peticion de
   * login llegaba y creaba la cuenta, pero el navegador descartaba la cookie en
   * silencio y la siguiente peticion devolvia 401.
   *
   * Al pasar por el proxy, la respuesta le llega al navegador desde el propio
   * dominio de la aplicacion, asi que la cookie es de PRIMERA PARTE y ningun
   * navegador la bloquea. Como efecto secundario desaparece el CORS (ya no hay
   * peticion cross-origin) y se puede volver a `SameSite=Lax`, que restaura la
   * proteccion frente a CSRF que `None` obligaba a ceder.
   *
   * La alternativa habria sido un dominio propio con dos subdominios, que
   * resuelve lo mismo pero cuesta dinero.
   */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_ORIGIN}/:path*`,
      },
    ]
  },

  /**
   * Cabeceras de seguridad aplicadas a todas las rutas.
   *
   * No sustituyen a la proteccion del backend, pero endurecen el cliente. Son
   * especialmente relevantes en este proyecto: la sesion vive en una cookie
   * httpOnly, y estas cabeceras reducen la superficie de los ataques que
   * podrian intentar abusar de ella.
   */
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // Impide que el navegador reinterprete el tipo MIME declarado.
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          // Bloquea el renderizado del sitio dentro de un iframe ajeno, que es
          // el vector del clickjacking.
          { key: 'X-Frame-Options', value: 'DENY' },
          // Limita la informacion de procedencia enviada a terceros.
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          // Desactiva APIs del navegador que esta aplicacion no usa.
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ]
  },
}

export default nextConfig
