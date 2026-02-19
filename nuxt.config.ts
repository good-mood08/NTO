// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  fonts:false,
  ui: {
    theme: {
      colors: [
        'primary',
        'secondary',
        'tertiary',
        'info',
        'success',
        'warning',
        'error'
      ]
    }
  },

  modules: ['@nuxt/ui', '@vueuse/nuxt'],
  css: ['~/assets/css/main.css']

})