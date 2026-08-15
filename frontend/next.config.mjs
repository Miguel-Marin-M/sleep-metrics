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
