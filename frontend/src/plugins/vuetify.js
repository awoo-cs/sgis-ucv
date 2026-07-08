import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: {
    defaultTheme: localStorage.getItem('sgis_theme') === 'light' ? 'sgis' : 'sgisDark',
    themes: {
      sgis: {
        dark: false,
        colors: {
          background:      '#F2F2F2',
          surface:         '#FFFFFF',
          primary:         '#0A0A0A',
          secondary:       '#6B6B6B',
          accent:          '#0A0A0A',
          error:           '#D92B2B',
          warning:         '#B36B00',
          info:            '#0A0A0A',
          success:         '#2D9A46',
          'on-background': '#111111',
          'on-surface':    '#111111',
          'on-primary':    '#FFFFFF',
        },
      },
      sgisDark: {
        dark: true,
        colors: {
          background:      '#07040F',
          surface:         '#0E0920',
          primary:         '#8B5CF6',
          secondary:       '#8F87B8',
          accent:          '#38BDF8',
          error:           '#F87171',
          warning:         '#FBBF24',
          info:            '#38BDF8',
          success:         '#34D399',
          'on-background': '#F0EDFA',
          'on-surface':    '#F0EDFA',
          'on-primary':    '#FFFFFF',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      variant: 'flat',
      style: "font-family: 'Inter', sans-serif; font-weight: 500; letter-spacing: 0.01em;",
    },
    VCard: { elevation: 0 },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect:    { variant: 'outlined', density: 'comfortable' },
    VTextarea:  { variant: 'outlined' },
  },
})
