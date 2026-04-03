import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Bot, AlertTriangle, CheckCircle2, XCircle, Mail, Rocket, User } from 'lucide-react'
import { API_BASE, LINKS, COMPANY, STATS_FALLBACK, ICONS } from './config'
import './index.css'

// Brand icon
const Github = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d={ICONS.github} />
  </svg>
)

// =============================================================================
// HERO - Single screen, no scroll needed for core message
// =============================================================================
function Hero({ stats }) {
  return (
    <section className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(0,255,209,0.05)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(255,71,87,0.03)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,209,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,209,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />
      </div>

      {/* Nav - Full width at top */}
      <nav className="relative z-20 flex items-center justify-between px-8 py-6">
        <Link to="/" className="flex items-center gap-3">
          <Shield className="w-10 h-10 text-cyan" />
          <span className="text-2xl font-bold text-white">VetoNet</span>
        </Link>
        <div className="hidden md:flex items-center gap-8">
          <a href="#how-it-works" className="text-smoke hover:text-white transition-colors">How it Works</a>
          <a href="#integration" className="text-smoke hover:text-white transition-colors">Integration</a>
          <a href="#pricing" className="text-smoke hover:text-white transition-colors">Pricing</a>
          <Link to="/challenge" className="text-smoke hover:text-white transition-colors">Red Team</Link>
        </div>
        <div className="flex items-center gap-5">
          <a href={LINKS.github} target="_blank" rel="noopener noreferrer" className="text-ash hover:text-white transition-colors">
            <Github className="w-6 h-6" />
          </a>
          <Link to="/auth"
             className="px-5 py-2.5 bg-white text-void font-medium rounded-lg hover:bg-white/90 transition-colors">
            Sign Up
          </Link>
        </div>
      </nav>

      {/* Hero content */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="max-w-6xl mx-auto w-full relative z-10">

        {/* Main content - centered */}
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan/10 border border-cyan/20 text-cyan text-sm font-mono mb-8">
            <div className="w-2 h-2 rounded-full bg-cyan animate-pulse" />
            PROOF OF INTENT
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-8 leading-tight">
            Ship autonomous agents,<br />
            not <span className="text-coral">liability</span>
          </h1>

          <p className="text-smoke text-lg md:text-xl mb-10 max-w-xl mx-auto">
            AI agents hallucinate. They get prompt-injected.
            VetoNet validates every transaction before it executes.
          </p>

          {/* Stats row */}
          <div className="flex items-center justify-center gap-8 mb-10">
            <div>
              <div className="text-3xl font-bold text-white">{stats.total_attempts.toLocaleString()}</div>
              <div className="text-ash text-sm">attacks tested</div>
            </div>
            <div className="w-px h-12 bg-slate" />
            <div>
              <div className="text-3xl font-bold text-lime">{(100 - stats.bypass_rate).toFixed(1)}%</div>
              <div className="text-ash text-sm">blocked</div>
            </div>
            <div className="w-px h-12 bg-slate" />
            <div>
              <div className="text-3xl font-bold text-coral">{stats.bypass_rate}%</div>
              <div className="text-ash text-sm">bypassed</div>
            </div>
          </div>

          {/* CTAs */}
          <div className="flex items-center justify-center gap-4">
            <Link to="/auth"
               className="px-6 py-3 bg-white text-void font-semibold rounded-lg hover:bg-white/90 transition-colors flex items-center gap-2">
              <Rocket className="w-4 h-4" />
              Sign Up Now
            </Link>
            <a href={LINKS.github} target="_blank" rel="noopener noreferrer"
               className="px-6 py-3 border border-slate text-white font-medium rounded-lg hover:border-ash transition-colors">
              View Code
            </a>
          </div>
        </div>
      </div>
      </div>
    </section>
  )
}

// =============================================================================
// FULL FLOW VISUALIZATION - Complete picture from user to outcome
// =============================================================================
function DefenseTree() {
  return (
    <section id="how-it-works" className="py-20 px-6 border-t border-slate/30 overflow-hidden scroll-mt-20">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
            How VetoNet Works
          </h2>
          <p className="text-smoke text-sm">
            From user intent to safe execution
          </p>
        </div>

        {/* Full flow visualization */}
        <div className="relative">

          {/* === TOP ROW: User → VetoNet Anchor → Agent === */}
          <div className="flex flex-wrap items-start justify-center gap-4 mb-6">

            {/* User Input */}
            <div className="bg-obsidian border border-cyan/30 rounded-xl p-4 max-w-xs">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg bg-cyan/20 flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-cyan" />
                </div>
                <span className="text-xs text-ash font-mono">USER</span>
                <span className="text-slate ml-auto">→</span>
              </div>
              <div className="text-cyan text-sm">
                "Book me a flight SFO→Tokyo, Dec 17-Jan 1, under $700"
              </div>
            </div>

            {/* VetoNet Anchors */}
            <div className="bg-obsidian border border-cyan/50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg bg-cyan/20 flex items-center justify-center">
                  <Shield className="w-3.5 h-3.5 text-cyan" />
                </div>
                <span className="text-xs text-cyan font-mono">VETONET ANCHOR</span>
                <span className="text-slate ml-auto">→</span>
              </div>
              <div className="text-xs text-smoke font-mono space-y-0.5">
                <div>route: SFO → NRT/HND</div>
                <div>dates: 2026-12-17 to 2027-01-01</div>
                <div>max_price: $700</div>
              </div>
            </div>

            {/* Agent Searches */}
            <div className="bg-obsidian border border-white/20 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <span className="text-xs text-ash font-mono">AGENT SEARCHING...</span>
              </div>
              <div className="text-xs font-mono space-y-0.5">
                <div className="text-smoke">google.com/flights</div>
                <div className="text-smoke">kayak.com</div>
                <div className="text-coral">cheapflights-deals.xyz</div>
                <div className="text-smoke">united.com</div>
              </div>
            </div>
          </div>

          {/* === Agent returns compromised payload === */}
          <div className="flex justify-center mb-6">
            <div className="bg-obsidian border border-coral/50 rounded-xl p-4 max-w-md">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg bg-coral/20 flex items-center justify-center">
                  <AlertTriangle className="w-3.5 h-3.5 text-coral" />
                </div>
                <span className="text-xs text-coral font-mono">AGENT RETURNS PAYLOAD</span>
              </div>
              <div className="text-white text-sm mb-2">
                "Found a great deal! Japan Airlines via Kayak"
              </div>
              <div className="text-xs space-y-1 text-smoke">
                <div>route: SFO → NRT <span className="text-coral">(departs Dec 18, not 17)</span></div>
                <div>layover: <span className="text-coral">26hr in Seoul</span></div>
                <div>base fare: $649 <span className="text-coral">+ $89 seat selection + $199 travel insurance</span></div>
                <div>total: <span className="text-coral font-bold">$937</span></div>
              </div>
            </div>
          </div>

          {/* === Connector === */}
          <div className="flex justify-center mb-4">
            <div className="w-px h-8 bg-gradient-to-b from-coral to-cyan" />
          </div>

          {/* === DEFENSE LAYERS LABEL === */}
          <div className="text-center mb-6">
            <span className="text-xs text-cyan font-mono bg-cyan/10 px-3 py-1 rounded-full">
              VETONET 3-LAYER DEFENSE
            </span>
          </div>

          {/* Defense layers - horizontal */}
          <div className="grid md:grid-cols-3 gap-4 mb-8">
            {/* Layer 1 */}
            <div className="bg-obsidian border border-cyan/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-cyan/20 flex items-center justify-center text-cyan font-bold">1</div>
                <div>
                  <div className="text-cyan font-medium text-sm">Deterministic</div>
                  <div className="text-xs text-ash font-mono">&lt;1ms</div>
                </div>
              </div>
              <div className="text-xs text-smoke space-y-1 mb-3">
                <div>✓ Price limits</div>
                <div>✓ Vendor verification</div>
                <div>✓ +8 more rules</div>
              </div>
              <div className="text-right">
                <span className="text-cyan font-bold">~70%</span>
                <span className="text-ash text-xs ml-1">blocked</span>
              </div>
            </div>

            {/* Layer 2 */}
            <div className="bg-obsidian border border-violet-500/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center text-violet-400 font-bold">2</div>
                <div>
                  <div className="text-violet-400 font-medium text-sm">ML Classifier</div>
                  <div className="text-xs text-ash font-mono">~50ms</div>
                </div>
              </div>
              <div className="text-xs text-smoke space-y-1 mb-3">
                <div>✓ 4,000+ patterns</div>
                <div>✓ Sentence embeddings</div>
                <div>✓ Real attack training</div>
              </div>
              <div className="text-right">
                <span className="text-violet-400 font-bold">~25%</span>
                <span className="text-ash text-xs ml-1">blocked</span>
              </div>
            </div>

            {/* Layer 3 */}
            <div className="bg-obsidian border border-lime/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-lime/20 flex items-center justify-center text-lime font-bold">3</div>
                <div>
                  <div className="text-lime font-medium text-sm">LLM Semantic</div>
                  <div className="text-xs text-ash font-mono">~200ms</div>
                </div>
              </div>
              <div className="text-xs text-smoke space-y-1 mb-3">
                <div>✓ Intent vs payload</div>
                <div>✓ NL reasoning</div>
                <div>✓ Edge cases</div>
              </div>
              <div className="text-right">
                <span className="text-lime font-bold">~5%</span>
                <span className="text-ash text-xs ml-1">blocked</span>
              </div>
            </div>
          </div>

          {/* === OUTCOME === */}
          <div className="flex justify-center">
            <div className="bg-obsidian border border-coral/50 rounded-xl p-5 text-center max-w-sm">
              <div className="flex items-center justify-center gap-2 mb-2">
                <XCircle className="w-5 h-5 text-coral" />
                <span className="text-coral text-lg font-bold">VETOED</span>
              </div>
              <div className="text-xs text-ash font-mono bg-carbon rounded px-3 py-2 text-left space-y-1">
                <div><span className="text-coral">✗</span> total $937 exceeds $700 limit</div>
                <div><span className="text-coral">✗</span> departure Dec 18 ≠ Dec 17</div>
                <div><span className="text-coral">✗</span> hidden fees detected: $288</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// =============================================================================
// INTEGRATION SECTION - Code snippets
// =============================================================================
function Integration() {
  const [copied, setCopied] = useState(false)

  const code = `from vetonet import VetoNet

veto = VetoNet()  # Uses API key from env

# Agent found something to buy...
purchase = agent.find_best_option()

# Verify before any purchase
result = veto.verify(
    intent=user_request,
    payload=purchase
)
if result.approved:
    execute_purchase(purchase)`

  const copyCode = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section id="integration" className="py-20 px-6 border-t border-slate/30 scroll-mt-20">
      <div className="max-w-5xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left: Text */}
          <div>
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Integrate in minutes
            </h2>
            <p className="text-smoke mb-8">
              Three simple steps. Works for any transaction type — flights, shoes, subscriptions, anything.
            </p>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan/20 flex items-center justify-center text-cyan font-bold text-sm flex-shrink-0">1</div>
                <div>
                  <div className="text-white font-medium">Install the SDK</div>
                  <div className="text-smoke text-sm font-mono">pip install vetonet</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan/20 flex items-center justify-center text-cyan font-bold text-sm flex-shrink-0">2</div>
                <div>
                  <div className="text-white font-medium">Add your API key</div>
                  <div className="text-smoke text-sm">Set <span className="font-mono">VETONET_API_KEY</span> in your .env file</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan/20 flex items-center justify-center text-cyan font-bold text-sm flex-shrink-0">3</div>
                <div>
                  <div className="text-white font-medium">Verify before purchase</div>
                  <div className="text-smoke text-sm">One call to <span className="font-mono">verify()</span> before any transaction</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Code */}
          <div>
            <div className="bg-obsidian border border-slate rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate bg-carbon">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-coral/60" />
                  <div className="w-3 h-3 rounded-full bg-amber/60" />
                  <div className="w-3 h-3 rounded-full bg-lime/60" />
                </div>
                <span className="text-xs text-ash font-mono">example.py</span>
                <button
                  onClick={copyCode}
                  className="text-ash hover:text-white transition-colors text-xs font-mono"
                >
                  {copied ? '✓ copied' : 'copy'}
                </button>
              </div>
              <pre className="p-4 text-sm font-mono overflow-x-auto">
                <code className="text-smoke">
                  <span className="text-violet-400">from</span> <span className="text-cyan">vetonet</span> <span className="text-violet-400">import</span> <span className="text-white">VetoNet</span>{'\n\n'}
                  <span className="text-white">veto</span> = <span className="text-cyan">VetoNet</span>()  <span className="text-ash"># Uses API key from env</span>{'\n\n'}
                  <span className="text-ash"># Agent found something to buy...</span>{'\n'}
                  <span className="text-white">purchase</span> = <span className="text-white">agent</span>.<span className="text-lime">find_best_option</span>(){'\n\n'}
                  <span className="text-ash"># Verify before any purchase</span>{'\n'}
                  <span className="text-white">result</span> = <span className="text-white">veto</span>.<span className="text-lime">verify</span>({'\n'}
                  {'    '}<span className="text-white">intent</span>=<span className="text-white">user_request</span>,{'\n'}
                  {'    '}<span className="text-white">payload</span>=<span className="text-white">purchase</span>{'\n'}
                  ){'\n'}
                  <span className="text-violet-400">if</span> <span className="text-white">result</span>.<span className="text-white">approved</span>:{'\n'}
                  {'    '}<span className="text-lime">execute_purchase</span>(<span className="text-white">purchase</span>)
                </code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// =============================================================================
// PRICING
// =============================================================================
function Pricing() {
  return (
    <section id="pricing" className="py-20 px-6 border-t border-slate/30 scroll-mt-20">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
            Simple pricing
          </h2>
          <p className="text-smoke">
            Start free. Scale when you need to.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          {/* Free tier */}
          <div className="bg-obsidian border border-slate rounded-xl p-6">
            <div className="mb-6">
              <div className="text-white font-semibold text-lg mb-1">Open Source</div>
              <div className="text-3xl font-bold text-white">Free</div>
              <div className="text-ash text-sm">forever</div>
            </div>
            <ul className="space-y-3 mb-8 text-sm">
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Full SDK code
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                10 deterministic checks
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Bring your own LLM
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Self-hosted
              </li>
              <li className="flex items-center gap-2 text-ash">
                <XCircle className="w-4 h-4 text-slate flex-shrink-0" />
                <span className="line-through">ML classifier</span>
              </li>
            </ul>
            <a href={LINKS.github} target="_blank" rel="noopener noreferrer"
               className="block w-full py-3 border border-slate text-white font-medium rounded-lg hover:border-ash transition-colors text-center">
              View on GitHub
            </a>
          </div>

          {/* Pro tier */}
          <div className="bg-obsidian border border-cyan/50 rounded-xl p-6 relative">
            <div className="absolute -top-3 left-6">
              <span className="bg-cyan text-void text-xs font-bold px-3 py-1 rounded-full">
                EARLY ACCESS
              </span>
            </div>
            <div className="mb-6">
              <div className="text-cyan font-semibold text-lg mb-1">API</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl text-ash line-through">$49/mo</span>
                <span className="text-3xl font-bold text-lime">Free</span>
              </div>
              <div className="text-cyan text-sm">Limited early access</div>
            </div>
            <ul className="space-y-3 mb-8 text-sm">
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Everything in Free
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Trained ML classifier
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                LLM semantic fallback
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                Sub-100ms latency
              </li>
              <li className="flex items-center gap-2 text-smoke">
                <CheckCircle2 className="w-4 h-4 text-cyan flex-shrink-0" />
                No LLM costs on your side
              </li>
            </ul>
            <Link to="/auth"
               className="block w-full py-3 bg-cyan text-void font-semibold rounded-lg hover:bg-cyan/90 transition-colors text-center">
              Get API Key
            </Link>
          </div>
        </div>

        <p className="text-center text-ash text-sm mt-8">
          Need enterprise? <a href={LINKS.calendly} target="_blank" rel="noopener noreferrer" className="text-cyan hover:underline">Book a call</a>
        </p>
      </div>
    </section>
  )
}

// =============================================================================
// CTA - Final call to action
// =============================================================================
function CTA() {
  return (
    <section className="py-20 px-6 border-t border-slate/30 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,255,209,0.08)_0%,transparent_70%)]" />

      <div className="max-w-2xl mx-auto text-center relative z-10">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
          Stop prompt injection<br />before it costs you
        </h2>
        <p className="text-smoke text-lg mb-8">
          Your agent is one bad prompt away from a lawsuit.<br />
          VetoNet catches it before it executes.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link to="/auth"
             className="px-8 py-4 bg-white text-void font-semibold rounded-lg hover:bg-white/90 transition-colors flex items-center gap-2">
            <Rocket className="w-5 h-5" />
            Get API Key
          </Link>
          <a href={LINKS.calendly} target="_blank" rel="noopener noreferrer"
             className="px-8 py-4 border border-slate text-white font-medium rounded-lg hover:border-ash transition-colors">
            Book Demo
          </a>
        </div>
      </div>
    </section>
  )
}

// =============================================================================
// FOOTER - Minimal
// =============================================================================
function Footer() {
  return (
    <footer className="border-t border-slate/30 py-8 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <div className="text-ash text-sm">
          {COMPANY.name} - {COMPANY.concept}
        </div>
        <a href={`mailto:${LINKS.email}`} className="text-ash hover:text-white text-sm transition-colors flex items-center gap-2">
          <Mail className="w-4 h-4" />
          {LINKS.email}
        </a>
      </div>
    </footer>
  )
}

// =============================================================================
// MAIN EXPORT
// =============================================================================
export default function LandingPage({ stats: propStats, children }) {
  const [stats, setStats] = useState(STATS_FALLBACK)

  // Fetch real stats from Railway API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/stats`)
        if (res.ok) {
          const data = await res.json()
          if (data.total_attempts > 0) {
            setStats({
              total_attempts: data.total_attempts,
              blocked: data.blocked,
              bypassed: data.bypassed,
              bypass_rate: data.bypass_rate,
            })
          }
        }
      } catch (e) {
        console.error('Stats fetch failed, using fallback')
      }
    }
    fetchStats()
  }, [])

  // Use prop stats if provided, otherwise use fetched stats
  const displayStats = propStats?.total_attempts > 0 ? propStats : stats

  return (
    <div className="min-h-screen bg-void">
      <Hero stats={displayStats} />
      <DefenseTree />
      <Integration />
      <Pricing />
      <CTA />

      {/* Playground section - only if children provided */}
      {children && (
        <section className="py-16 px-6 border-t border-slate/30">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-xl font-bold text-white mb-8">Try it yourself</h2>
            {children}
          </div>
        </section>
      )}

      <Footer />
    </div>
  )
}
