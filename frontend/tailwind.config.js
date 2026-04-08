/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['"Outfit"', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
          muted: 'rgb(var(--surface-muted) / <alpha-value>)',
          elevated: 'rgb(var(--surface-elevated) / <alpha-value>)',
        },
        content: {
          DEFAULT: 'rgb(var(--content) / <alpha-value>)',
          muted: 'rgb(var(--content-muted) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent) / <alpha-value>)',
          muted: 'rgb(var(--accent-muted) / <alpha-value>)',
        },
        border: 'rgb(var(--border) / <alpha-value>)',
      },
      boxShadow: {
        soft: '0 4px 24px -4px rgb(0 0 0 / 0.08), 0 8px 48px -12px rgb(0 0 0 / 0.12)',
        glow: '0 0 0 1px rgb(var(--accent) / 0.25), 0 12px 40px -8px rgb(var(--accent) / 0.35)',
        card: '0 0 0 1px rgb(255 255 255 / 0.05) inset, 0 4px 32px -10px rgb(0 0 0 / 0.55)',
        'card-hover':
          '0 0 0 1px rgb(var(--accent) / 0.18) inset, 0 12px 48px -12px rgb(var(--accent) / 0.15)',
        'inner-glow': 'inset 0 1px 0 0 rgb(255 255 255 / 0.07)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        mesh: `
          radial-gradient(ellipse 100% 70% at 50% -25%, rgb(var(--accent) / 0.2), transparent 55%),
          radial-gradient(ellipse 55% 45% at 100% 0%, rgb(168 85 247 / 0.09), transparent 50%),
          radial-gradient(ellipse 50% 40% at 0% 100%, rgb(34 211 238 / 0.08), transparent 50%)
        `,
      },
      keyframes: {
        pulseSlow: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.65', transform: 'scale(1.15)' },
        },
        borderGlow: {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        cardEnter: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        pulseSlow: 'pulseSlow 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        borderGlow: 'borderGlow 3s ease-in-out infinite',
        shimmer: 'shimmer 2s infinite',
        cardEnter: 'cardEnter 0.22s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
    },
  },
  plugins: [],
}
