import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion'
import { ArrowRight, Brain, ChevronDown, CircleCheckBig, Radar, Sparkles, Waves } from 'lucide-react'
import ThemeToggle from '../components/ui/ThemeToggle'

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'platform', label: 'Platform' },
  { id: 'journey', label: 'Journey' },
  { id: 'faq', label: 'FAQ' },
]

const TRUSTED_BY = [
  'Axis Finance Team',
  'Urban Retail Group',
  'Mahindra Fleet Ops',
  'Razorpay Commerce',
  'IDFC First Desk',
  'TVS Mobility Ops',
]

const MODULES = [
  {
    id: 'live-intelligence',
    label: 'Live Intelligence',
    title: 'Real-time spending awareness',
    summary:
      'Monitor transaction behavior as it happens, with meaningful categorisation and confidence-aware interpretation.',
    points: ['Continuous feed visibility', 'Clarity on transaction intent', 'Faster decision making'],
  },
  {
    id: 'statement-experience',
    label: 'Statement Experience',
    title: 'Unified statement understanding',
    summary:
      'Bring statements from multiple formats into one clean experience and quickly discover the transactions that matter.',
    points: ['Multi-format ingestion', 'Search and filter simplicity', 'Consistent transaction context'],
  },
  {
    id: 'analytics-insights',
    label: 'Analytics',
    title: 'Behavior-driven spending insights',
    summary:
      'Explore trends, patterns, and category movement to understand where money flows and how behavior changes over time.',
    points: ['Trend exploration', 'Category and merchant visibility', 'Budget-oriented perspective'],
  },
  {
    id: 'anomaly-signals',
    label: 'Anomaly Signals',
    title: 'Early detection of unusual activity',
    summary:
      'Surface unusual spending moments quickly so users can review, accept, or escalate with confidence.',
    points: ['Risk-focused signal view', 'Action-first review flow', 'Better financial control'],
  },
  {
    id: 'coach-layer',
    label: 'AI Coach',
    title: 'Guided financial conversations',
    summary:
      'Turn raw spend data into understandable insights through conversational guidance and monthly narratives.',
    points: ['Contextual recommendations', 'Natural language guidance', 'Insight-to-action clarity'],
  },
  {
    id: 'model-observability',
    label: 'Model Quality',
    title: 'Confidence in platform intelligence',
    summary:
      'Keep trust high through transparent model quality visibility and continuous improvement pathways.',
    points: ['Model quality transparency', 'Feedback-driven evolution', 'Operational reliability'],
  },
]

const JOURNEY = [
  {
    step: '01',
    title: 'Connect',
    text: 'Bring your live activity and statements into one place for a single source of financial truth.',
  },
  {
    step: '02',
    title: 'Understand',
    text: 'Use dynamic analytics and anomaly signals to discover behavior patterns and outliers.',
  },
  {
    step: '03',
    title: 'Act',
    text: 'Use guided recommendations to make timely and confident money decisions.',
  },
]

const FAQ = [
  {
    q: 'What exactly is this project?',
    a: 'It is a personal expense intelligence platform that combines live monitoring, statement understanding, behavior analytics, anomaly detection, and guided financial insights.',
  },
  {
    q: 'Why is this better than a basic tracker?',
    a: 'A basic tracker records values. This platform helps interpret values with context, risk awareness, and actionable guidance.',
  },
  {
    q: 'Is this only for one type of user?',
    a: 'No. It is designed for individual users and teams who need clarity, speed, and confidence in expense-related decisions.',
  },
]

const IMPACT_STATS = [
  { value: '50K+', label: 'Transactions interpreted' },
  { value: '99.9%', label: 'Pipeline reliability target' },
  { value: '<2s', label: 'Interactive response feel' },
]

const EXPERIENCE_HIGHLIGHTS = [
  'Dynamic pre-login storytelling',
  'Responsive interaction patterns',
  'Action-focused data visibility',
  'AI-guided decision support',
]

function SectionTitle({ kicker, title, body }) {
  return (
    <div className="max-w-3xl">
      <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">{kicker}</p>
      <h2 className="mt-2 font-display text-2xl font-bold text-content sm:text-3xl">{title}</h2>
      {body && <p className="mt-3 text-sm leading-relaxed text-content-muted sm:text-base">{body}</p>}
    </div>
  )
}

export default function HomePage() {
  const reduceMotion = useReducedMotion()
  const [activeModule, setActiveModule] = useState(MODULES[0].id)
  const [openFaq, setOpenFaq] = useState(-1)
  const [activeStep, setActiveStep] = useState(0)
  const [activeSection, setActiveSection] = useState('overview')
  const [spotlight, setSpotlight] = useState({ x: 0, y: 0, active: false })
  const [highlightIndex, setHighlightIndex] = useState(0)
  const [canHover, setCanHover] = useState(false)
  const [panelTilt, setPanelTilt] = useState({ rx: 0, ry: 0 })
  const { scrollYProgress } = useScroll()
  const progressScaleX = useSpring(scrollYProgress, { stiffness: 110, damping: 30, mass: 0.2 })
  const heroY = useTransform(scrollYProgress, [0, 0.25], [0, -26])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.22], [1, 0.82])

  const activeModuleData = useMemo(
    () => MODULES.find((module) => module.id === activeModule) ?? MODULES[0],
    [activeModule],
  )

  useEffect(() => {
    const mq = window.matchMedia('(hover: hover) and (pointer: fine)')
    const apply = () => setCanHover(mq.matches)
    apply()
    mq.addEventListener?.('change', apply)
    return () => mq.removeEventListener?.('change', apply)
  }, [])

  useEffect(() => {
    if (reduceMotion) return undefined
    const id = window.setInterval(() => {
      setActiveModule((prev) => {
        const index = MODULES.findIndex((m) => m.id === prev)
        const next = (index + 1) % MODULES.length
        return MODULES[next].id
      })
    }, 4200)
    return () => window.clearInterval(id)
  }, [reduceMotion])

  useEffect(() => {
    const sectionIds = NAV_ITEMS.map((i) => i.id)
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean)
    if (!elements.length) return undefined

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible[0]?.target?.id) setActiveSection(visible[0].target.id)
      },
      { rootMargin: '-35% 0px -45% 0px', threshold: [0.2, 0.4, 0.6] },
    )

    elements.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (reduceMotion) return undefined
    const id = window.setInterval(() => {
      setHighlightIndex((prev) => (prev + 1) % EXPERIENCE_HIGHLIGHTS.length)
    }, 2600)
    return () => window.clearInterval(id)
  }, [reduceMotion])

  return (
    <div
      className="relative min-h-svh overflow-hidden"
      onMouseMove={(e) => {
        if (!canHover) return
        const rect = e.currentTarget.getBoundingClientRect()
        setSpotlight({ x: e.clientX - rect.left, y: e.clientY - rect.top, active: true })
      }}
      onMouseLeave={() => setSpotlight((s) => ({ ...s, active: false }))}
    >
      <motion.div
        className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-1 origin-left bg-gradient-to-r from-sky-500 via-cyan-400 to-violet-400"
        style={{ scaleX: progressScaleX }}
      />
      <motion.div
        aria-hidden
        className="spotlight-glow pointer-events-none absolute z-0 h-72 w-72 rounded-full"
        animate={{
          opacity: spotlight.active && canHover ? 0.36 : 0,
          x: spotlight.x - 144,
          y: spotlight.y - 144,
        }}
        transition={{ type: 'spring', stiffness: 90, damping: 18, mass: 0.5 }}
      />
      <motion.div
        aria-hidden
        className="hero-orb pointer-events-none absolute -left-24 top-10 h-64 w-64 rounded-full bg-sky-400/20 blur-3xl"
        animate={{ x: [0, 24, -10, 0], y: [0, -18, 10, 0] }}
        transition={{ repeat: Infinity, duration: 12, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden
        className="hero-orb pointer-events-none absolute -right-24 top-24 h-72 w-72 rounded-full bg-violet-400/20 blur-3xl"
        animate={{ x: [0, -24, 10, 0], y: [0, 16, -8, 0] }}
        transition={{ repeat: Infinity, duration: 14, ease: 'easeInOut' }}
      />
      <div className="pointer-events-none absolute inset-0">
        {Array.from({ length: 12 }).map((_, i) => (
          <span
            key={`particle-${i}`}
            className="float-particle"
            style={{
              left: `${8 + i * 8}%`,
              top: `${10 + ((i * 9) % 75)}%`,
              animationDelay: `${(i % 6) * 0.8}s`,
              animationDuration: `${8 + (i % 5)}s`,
            }}
          />
        ))}
      </div>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-3 pb-14 pt-4 sm:px-6 sm:pb-24 sm:pt-10">
        <motion.nav
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="sticky top-[max(0.5rem,env(safe-area-inset-top,0px))] z-40 mb-6 rounded-2xl border border-theme-subtle bg-surface/85 px-2.5 py-2 backdrop-blur-xl sm:mb-8 sm:px-3"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <img src="/logo-mark.svg" alt="Expense Intelligence" className="h-8 w-8 rounded-xl" />
              <span className="max-[360px]:hidden text-xs font-bold uppercase tracking-[0.18em] text-content-muted">
                Expense Intelligence
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`link-underline hidden rounded-full px-2 py-1 text-xs font-semibold md:inline-flex ${
                    activeSection === item.id
                      ? 'bg-sky-500/15 text-content ring-1 ring-sky-400/30'
                      : 'text-content-muted hover:text-content'
                  }`}
                >
                  {item.label}
                </a>
              ))}
              <div className="theme-toggle-well rounded-full p-1">
                <ThemeToggle />
              </div>
              <Link to="/app" className="btn-primary rounded-xl px-2.5 py-1.5 text-[11px] sm:px-3 sm:text-xs">
                Open App
              </Link>
            </div>
          </div>
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-0.5 md:hidden scrollbar-thin">
            {NAV_ITEMS.map((item) => (
              <a
                key={`mobile-${item.id}`}
                href={`#${item.id}`}
                className={`shrink-0 rounded-full border px-3 py-1.5 text-[11px] font-semibold transition ${
                  activeSection === item.id
                    ? 'border-sky-400/40 bg-sky-500/15 text-content'
                    : 'border-theme-subtle bg-surface-elevated/60 text-content-muted hover:text-content'
                }`}
              >
                {item.label}
              </a>
            ))}
          </div>
        </motion.nav>

        <section id="overview" className="section-shell border-theme-subtle pb-10 sm:pb-12">
          <motion.div
            className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end"
            style={{ y: heroY, opacity: heroOpacity }}
          >
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-sky-400/30 bg-sky-500/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-200">
                <Sparkles className="h-3.5 w-3.5" />
                Personal Expense Intelligence Platform
              </p>
              <h1 className="mt-5 max-w-4xl font-display text-3xl font-bold leading-[1.08] heading-gradient sm:text-5xl lg:text-6xl">
                One platform to monitor, understand, and improve spending decisions
              </h1>
              <p className="mt-5 max-w-2xl text-sm leading-relaxed text-content-muted sm:text-base">
                This experience is designed like a product website before login: clear narrative, complete project
                information, interactive sections, and smooth responsiveness across devices.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link to="/app" className="btn-primary cta-pop w-full justify-center sm:w-auto">
                  Go to Main Application
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a href="#platform" className="btn-ghost w-full justify-center sm:w-auto">
                  Explore platform details
                </a>
              </div>
            </div>

            <div className="space-y-3 rounded-2xl border border-theme-subtle bg-surface-elevated/55 p-4 backdrop-blur-md">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-content-muted">
                What this project delivers
              </p>
              <div className="space-y-2">
                {[
                  'Live visibility into transaction behavior',
                  'Unified statement and spending understanding',
                  'AI-guided and risk-aware financial decision support',
                ].map((item) => (
                  <div key={item} className="flex items-start gap-2 text-sm text-content">
                    <CircleCheckBig className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          <div className="mt-10 overflow-hidden rounded-2xl border border-theme-subtle bg-surface-elevated/40">
            <div className="marquee-track flex items-center gap-8 px-6 py-4">
              {[...TRUSTED_BY, ...TRUSTED_BY].map((name, idx) => (
                <span key={`${name}-${idx}`} className="marquee-item shrink-0 text-sm font-semibold text-content-muted">
                  {name}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-theme-subtle bg-surface-elevated/45 px-4 py-3">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-content-muted">
              Experience highlight
            </p>
            <AnimatePresence mode="wait" initial={false}>
              <motion.p
                key={highlightIndex}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.22 }}
                className="text-sm font-semibold text-content sm:text-base"
              >
                {EXPERIENCE_HIGHLIGHTS[highlightIndex]}
              </motion.p>
            </AnimatePresence>
          </div>
        </section>

        <motion.section
          id="platform"
          className="section-shell border-theme-subtle py-10 sm:py-12"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.35 }}
        >
          <SectionTitle
            kicker="Platform modules"
            title="Complete project information, organized like a product"
            body="Select any module to explore what it contributes to the overall platform experience."
          />

          <div className="mt-8 grid gap-8 lg:grid-cols-[0.42fr_0.58fr]">
            <div className="grid max-[420px]:grid-cols-1 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-1 lg:gap-2">
              {MODULES.map((module) => {
                const active = module.id === activeModule
                return (
                  <button
                    key={module.id}
                    type="button"
                    onClick={() => setActiveModule(module.id)}
                    className={`group flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition sm:min-h-[56px] ${
                      active
                        ? 'border-sky-400/45 bg-sky-500/10'
                        : 'border-theme-subtle bg-surface-elevated/45 hover:border-sky-400/30'
                    }`}
                  >
                    <span className={`text-xs font-semibold sm:text-sm ${active ? 'text-content' : 'text-content-muted group-hover:text-content'}`}>
                      {module.label}
                    </span>
                    <ArrowRight className={`h-4 w-4 transition ${active ? 'text-sky-500' : 'text-content-muted'}`} />
                  </button>
                )
              })}
            </div>

            <motion.div
              key={activeModuleData.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28 }}
              onMouseMove={(e) => {
                if (!canHover || reduceMotion) return
                const rect = e.currentTarget.getBoundingClientRect()
                const px = (e.clientX - rect.left) / rect.width
                const py = (e.clientY - rect.top) / rect.height
                const ry = (px - 0.5) * 6
                const rx = (0.5 - py) * 6
                setPanelTilt({ rx, ry })
              }}
              onMouseLeave={() => setPanelTilt({ rx: 0, ry: 0 })}
              style={{
                rotateX: panelTilt.rx,
                rotateY: panelTilt.ry,
                transformPerspective: 900,
              }}
              className="rounded-2xl border border-theme-subtle bg-gradient-to-b from-surface-elevated/70 to-surface-muted/35 p-5 transition-transform duration-200 sm:p-6"
            >
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em] text-accent">
                <Waves className="h-4 w-4" />
                {activeModuleData.label}
              </div>
              <h3 className="mt-3 font-display text-2xl font-bold text-content">{activeModuleData.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-content-muted sm:text-base">{activeModuleData.summary}</p>
              <div className="mt-6 border-t border-theme-subtle pt-4">
                <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.15em] text-content-muted">Key outcomes</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {activeModuleData.points.map((point) => (
                    <div key={point} className="inline-flex items-center gap-2 text-sm text-content-muted">
                      <CircleCheckBig className="h-4 w-4 text-emerald-400" />
                      <span>{point}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-5 border-t border-theme-subtle pt-4">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-content-muted">
                    Live section focus
                  </p>
                  <p className="text-xs text-content-muted">
                    {MODULES.findIndex((m) => m.id === activeModule) + 1}/{MODULES.length}
                  </p>
                </div>
                <div className="flex gap-1.5">
                  {MODULES.map((module) => (
                    <button
                      key={`dot-${module.id}`}
                      type="button"
                      onClick={() => setActiveModule(module.id)}
                      aria-label={`Show ${module.label}`}
                      className={`h-1.5 rounded-full transition-all ${
                        module.id === activeModule
                          ? 'w-8 bg-sky-500'
                          : 'w-3 bg-slate-300 dark:bg-slate-600'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {IMPACT_STATS.map((item) => (
              <motion.div
                key={item.label}
                whileHover={{ y: -2, scale: 1.01 }}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                className="rounded-xl border border-theme-subtle bg-surface-elevated/45 px-4 py-4"
              >
                <p className="font-display text-2xl font-bold text-content">{item.value}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-content-muted">{item.label}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.section
          id="journey"
          className="section-shell border-theme-subtle py-10 sm:py-12"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.35 }}
        >
          <SectionTitle
            kicker="User journey"
            title="How the full experience flows"
            body="A simple progression from incoming data to confident action."
          />

          <div className="mt-8 grid gap-0 border border-theme-subtle bg-surface-elevated/45 lg:grid-cols-3">
            {JOURNEY.map((item, idx) => (
              <div
                key={item.step}
                onMouseEnter={() => setActiveStep(idx)}
                className={`p-5 sm:p-6 ${
                  idx < JOURNEY.length - 1 ? 'border-b border-theme-subtle lg:border-b-0 lg:border-r' : ''
                } ${activeStep === idx ? 'bg-sky-500/5' : ''}`}
              >
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-content-muted">Step {item.step}</p>
                <h3 className="mt-2 font-display text-xl font-bold text-content">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-content-muted">{item.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              { label: 'Live intelligence', icon: Waves },
              { label: 'Risk awareness', icon: Radar },
              { label: 'Guided improvement', icon: Brain },
            ].map((signal) => {
              const Icon = signal.icon
              return (
                <motion.div
                  key={signal.label}
                  whileHover={{ y: -3, scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="flex items-center gap-2 border border-theme-subtle bg-surface-elevated/45 px-4 py-3 transition hover:border-sky-400/35"
                >
                  <Icon className="h-4 w-4 text-sky-500" />
                  <span className="text-sm font-semibold text-content">{signal.label}</span>
                </motion.div>
              )
            })}
          </div>
        </motion.section>

        <motion.section
          id="faq"
          className="pt-10 sm:pt-12"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.35 }}
        >
          <SectionTitle
            kicker="FAQs"
            title="Quick answers before you enter the app"
          />

          <div className="mt-6 divide-y divide-theme-subtle border border-theme-subtle bg-surface-elevated/45">
            {FAQ.map((item, idx) => {
              const open = openFaq === idx
              return (
                <motion.div key={item.q} whileHover={{ backgroundColor: 'rgb(56 189 248 / 0.04)' }}>
                  <button
                    type="button"
                    onClick={() => setOpenFaq((prev) => (prev === idx ? -1 : idx))}
                    className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left sm:px-5"
                  >
                    <span className="text-sm font-semibold text-content sm:text-base">{item.q}</span>
                    <ChevronDown className={`h-4 w-4 text-content-muted transition ${open ? 'rotate-180' : ''}`} />
                  </button>
                  <AnimatePresence initial={false}>
                    {open && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <p className="px-4 pb-4 text-sm leading-relaxed text-content-muted sm:px-5 sm:text-base">{item.a}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>

          <div className="mt-8 flex flex-col items-start justify-between gap-4 border border-sky-400/30 bg-gradient-to-r from-sky-500/10 to-cyan-500/5 p-4 sm:flex-row sm:items-center sm:p-5">
            <p className="text-sm font-medium text-content sm:text-base">
              Ready to continue? Open the main application and explore live intelligence in action.
            </p>
            <Link to="/app" className="btn-primary cta-pop w-full justify-center sm:w-auto">
              Enter Application
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

        </motion.section>
      </main>

    </div>
  )
}
