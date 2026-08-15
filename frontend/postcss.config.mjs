/**
 * Configuracion de PostCSS.
 *
 * Tailwind se ejecuta como plugin de PostCSS y autoprefixer anade los prefijos
 * de proveedor necesarios segun el navegador objetivo.
 *
 * @type {import('postcss-load-config').Config}
 */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}

export default config
