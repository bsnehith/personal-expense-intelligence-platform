import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../../context/ThemeContext'

export default function ThemeToggle({ className = '' }) {
  const { effective, setTheme } = useTheme()
  const isDark = effective === 'dark'

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className={`interactive-press relative flex h-8 w-16 items-center rounded-full border p-1 transition-all duration-300 focus-visible:ring-2 focus-visible:ring-accent
        ${isDark
          ? 'border-sky-400/40 bg-slate-800 shadow-[0_0_12px_rgb(56_189_248/0.25)]'
          : 'border-slate-300 bg-slate-200 shadow-inner-glow'
        } ${className}`}
    >
      {/* Track icons */}
      <Sun
        className={`absolute left-1.5 h-3.5 w-3.5 transition-opacity duration-200 ${isDark ? 'opacity-40 text-slate-400' : 'opacity-0'}`}
        strokeWidth={2.5}
        aria-hidden
      />
      <Moon
        className={`absolute right-1.5 h-3.5 w-3.5 transition-opacity duration-200 ${isDark ? 'opacity-0' : 'opacity-40 text-slate-500'}`}
        strokeWidth={2.5}
        aria-hidden
      />

      {/* Sliding thumb */}
      <span
        className={`relative z-10 flex h-6 w-6 items-center justify-center rounded-full shadow-md transition-all duration-300
          ${isDark
            ? 'translate-x-8 bg-sky-400'
            : 'translate-x-0 bg-white'
          }`}
      >
        {isDark ? (
          <Moon className="h-3.5 w-3.5 text-slate-900" strokeWidth={2.5} aria-hidden />
        ) : (
          <Sun className="h-3.5 w-3.5 text-amber-500" strokeWidth={2.5} aria-hidden />
        )}
      </span>
    </button>
  )
}
