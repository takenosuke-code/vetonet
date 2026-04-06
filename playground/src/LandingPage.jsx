import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, ShieldCheck, ShieldAlert, Bot, AlertTriangle, CheckCircle2, XCircle,
  Mail, Rocket, User, Terminal, Copy, Check, Lock, Activity, RotateCcw,
  ArrowRight, ShoppingCart, Package, Code2
} from 'lucide-react'
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
                "Found a great deal! Japan Airlines via <span className="text-coral">cheapflights-deals.xyz</span>"
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
// INTEGRATION SECTION - Full sandbox with code + live demo
// =============================================================================

const INTEGRATION_PRODUCTS = [
  {
    id: 'gift-card', name: 'Amazon Gift Card', price: 50, vendor: 'amazon.com',
    category: 'gift_card', safe: true, prompt: '$50 Amazon Gift Card', icon: '🎁',
  },
  {
    id: 'airpods', name: 'AirPods Pro 2', price: 249, vendor: 'apple.com',
    category: 'electronics', safe: true, prompt: 'Buy AirPods Pro 2 from Apple for under $250', icon: '🎧',
  },
  {
    id: 'macbook-scam', name: 'MacBook Pro "MEGA DEAL"', price: 999, vendor: 'cheap-macbooks.xyz',
    category: 'electronics', safe: false, prompt: 'MacBook Pro under $300', icon: '💻',
    attackNote: 'Price 3x over budget + sketchy vendor',
  },
  {
    id: 'netflix-trap', name: 'Netflix Gift Card', price: 25, vendor: 'netflix-gifts.io',
    category: 'subscription', safe: false, prompt: '$25 Netflix gift card, one-time', icon: '📺',
    attackNote: 'Hidden recurring charge + processing fee',
    hiddenFees: [{ name: 'Processing', amount: 9.99 }], isRecurring: true,
  },
]

const INTEGRATION_CHECKS = [
  { id: 'price', name: 'Price Limit' }, { id: 'quantity', name: 'Quantity' },
  { id: 'category', name: 'Category' }, { id: 'currency', name: 'Currency' },
  { id: 'vendor', name: 'Vendor' }, { id: 'anomaly', name: 'Anomaly' },
  { id: 'fees', name: 'Fees' }, { id: 'subscription', name: 'Recurring' },
  { id: 'semantic', name: 'Semantic' },
]

const CODE_SNIPPETS = {
  sdk: {
    label: 'SDK', filename: 'app.py',
    code: `from vetonet import VetoNet

veto = VetoNet(provider="groq", api_key="your-key")

result = veto.verify(
    intent="$50 Amazon Gift Card",
    payload={
        "item_description": "Amazon Gift Card",
        "unit_price": 50,
        "vendor": "amazon.com"
    }
)

if result.approved:
    process_payment()`,
  },
  langchain: {
    label: 'LangChain', filename: 'agent.py',
    code: `from vetonet.langchain import protected_tool, init

init(api_key="veto_sk_live_xxx")

@protected_tool
def buy_item(item: str, price: float, vendor: str) -> str:
    """Buy an item."""
    return execute_purchase(item, price, vendor)

# Done. One decorator = every transaction protected.`,
  },
  rest: {
    label: 'REST API', filename: 'terminal',
    code: `curl -X POST https://api.vetonet.dev/api/check \\
  -H "Authorization: Bearer veto_sk_live_xxx" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "$50 Amazon Gift Card",
    "payload": {
      "item_description": "Amazon Gift Card",
      "unit_price": 50,
      "vendor": "amazon.com"
    }
  }'`,
  },
}

const STEPS_BY_METHOD = {
  sdk: [
    { label: 'Install', cmd: 'pip install vetonet', icon: <Package className="w-5 h-5" /> },
    { label: 'Initialize', cmd: 'VetoNet(provider, api_key)', icon: <Code2 className="w-5 h-5" /> },
    { label: 'Verify', cmd: 'veto.verify(intent, payload)', icon: <Shield className="w-5 h-5" /> },
    { label: 'Ship it', cmd: 'Every transaction protected', icon: <Rocket className="w-5 h-5" /> },
  ],
  langchain: [
    { label: 'Install', cmd: 'pip install vetonet', icon: <Package className="w-5 h-5" /> },
    { label: 'Add one decorator', cmd: '@protected_tool', icon: <Code2 className="w-5 h-5" /> },
    { label: 'Ship it', cmd: 'Every transaction protected', icon: <Rocket className="w-5 h-5" /> },
  ],
  rest: [
    { label: 'Get API key', cmd: 'veto_sk_live_xxx', icon: <Lock className="w-5 h-5" /> },
    { label: 'POST /api/check', cmd: 'curl + JSON payload', icon: <Terminal className="w-5 h-5" /> },
    { label: 'Ship it', cmd: 'Every transaction protected', icon: <Rocket className="w-5 h-5" /> },
  ],
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

function Integration() {
  const [codeMethod, setCodeMethod] = useState('sdk')
  const [copied, setCopied] = useState(false)
  const [activeStep, setActiveStep] = useState(0)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [storePhase, setStorePhase] = useState('idle')
  const [storeCheck, setStoreCheck] = useState(-1)
  const [storeResult, setStoreResult] = useState(null)

  useEffect(() => {
    const stepCount = STEPS_BY_METHOD[codeMethod].length
    const timer = setInterval(() => {
      setActiveStep(s => (s + 1) % stepCount)
    }, 4000)
    return () => clearInterval(timer)
  }, [codeMethod])

  const copyCode = () => {
    navigator.clipboard.writeText(CODE_SNIPPETS[codeMethod].code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const runStorefrontDemo = async (product) => {
    setSelectedProduct(product)
    setStorePhase('locking')
    setStoreResult(null)
    setStoreCheck(-1)

    if (!product.safe) {
      try {
        const res = await fetch(`${API_BASE}/demo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: product.prompt, mode: 'compromised' })
        })
        if (res.ok) {
          const data = await res.json()
          await sleep(500)
          setStorePhase('shopping')
          await sleep(600)
          setStorePhase('scanning')
          const checks = data.result.checks
          for (let i = 0; i < checks.length; i++) {
            setStoreCheck(i)
            await sleep(180)
            if (!checks[i].passed) { await sleep(200); break }
          }
          await sleep(300)
          setStorePhase('result')
          setStoreResult(data)
          return
        }
      } catch (e) {
        console.log('API unavailable, using mock')
      }
    }

    await sleep(500)
    setStorePhase('shopping')
    await sleep(600)
    setStorePhase('scanning')
    const mockChecks = INTEGRATION_CHECKS.map((c, i) => ({
      ...c, passed: product.safe || i > 3,
      reason: !product.safe && i <= 3 ? 'Violation detected' : null
    }))
    for (let i = 0; i < mockChecks.length; i++) {
      setStoreCheck(i)
      await sleep(180)
      if (!mockChecks[i].passed) break
    }
    await sleep(300)
    setStorePhase('result')
    setStoreResult({
      intent: { item_category: product.category, max_price: product.price, quantity: 1 },
      payload: {
        item_description: product.name, unit_price: product.price,
        vendor: product.vendor, fees: product.hiddenFees || [],
        is_recurring: product.isRecurring || false
      },
      result: {
        approved: product.safe,
        checks: mockChecks,
        message: product.safe ? 'Approved' : 'Vetoed'
      }
    })
  }

  const resetStore = () => {
    setSelectedProduct(null)
    setStorePhase('idle')
    setStoreResult(null)
    setStoreCheck(-1)
  }

  const steps = STEPS_BY_METHOD[codeMethod]
  const snippet = CODE_SNIPPETS[codeMethod]

  return (
    <section id="integration" className="py-20 px-6 border-t border-slate/30 scroll-mt-20">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
            Protect Every Transaction in <span className="text-cyan">3 Lines</span>
          </h2>
          <p className="text-smoke text-sm md:text-base">Pick your integration method. That's it.</p>
        </div>

        {/* Step Stepper */}
        <div className={`grid gap-3 ${steps.length === 4 ? 'grid-cols-4' : 'grid-cols-3'}`}>
          {steps.map((step, i) => (
            <button
              key={i}
              onClick={() => setActiveStep(i)}
              className={`rounded-xl p-4 border text-left transition-all ${
                activeStep === i
                  ? 'border-cyan/40 bg-cyan/10 shadow-lg shadow-cyan/5'
                  : 'border-slate/30 bg-steel/20 hover:border-slate/50'
              }`}
            >
              <div className={`mb-2 ${activeStep === i ? 'text-cyan' : 'text-ash'}`}>
                {step.icon}
              </div>
              <div className="text-xs font-mono text-ash mb-1">STEP {i + 1}</div>
              <div className={`text-sm font-semibold mb-1 ${activeStep === i ? 'text-white' : 'text-smoke'}`}>
                {step.label}
              </div>
              <div className="text-[10px] font-mono text-ash truncate">{step.cmd}</div>
            </button>
          ))}
        </div>

        {/* Code Showcase */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="inline-flex p-1 rounded-xl bg-steel/50 border border-slate/50">
              {Object.entries(CODE_SNIPPETS).map(([key, val]) => (
                <button
                  key={key}
                  onClick={() => { setCodeMethod(key); setCopied(false); setActiveStep(0) }}
                  className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                    codeMethod === key
                      ? 'bg-cyan/20 text-cyan border border-cyan/30'
                      : 'text-smoke hover:text-white'
                  }`}
                >
                  {val.label}
                </button>
              ))}
            </div>
            <button
              onClick={copyCode}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-smoke hover:text-white border border-slate/30 hover:border-slate/50 transition-all"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-lime" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={codeMethod}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="rounded-2xl bg-[#0a0a0f] border border-slate/40 overflow-hidden"
            >
              <div className="flex items-center gap-2 px-4 py-3 border-b border-slate/30 bg-obsidian/80">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-coral/60" />
                  <div className="w-3 h-3 rounded-full bg-amber/60" />
                  <div className="w-3 h-3 rounded-full bg-lime/60" />
                </div>
                <div className="flex items-center gap-1.5 ml-2">
                  <Terminal className="w-3.5 h-3.5 text-ash" />
                  <span className="text-xs font-mono text-ash">{snippet.filename}</span>
                </div>
              </div>
              <pre className="p-5 text-sm font-mono leading-relaxed overflow-x-auto">
                <code className="text-smoke">{snippet.code.split('\n').map((line, i) => (
                  <span key={i}>
                    {line.startsWith('#') ? <span className="text-ash">{line}</span> : line}
                    {'\n'}
                  </span>
                ))}</code>
              </pre>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-slate/50 to-transparent" />
          <span className="text-xs font-mono text-ash uppercase tracking-wider">See it in action</span>
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-slate/50 to-transparent" />
        </div>

        {/* Mock Storefront */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Left: Product cards */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart className="w-4 h-4 text-cyan" />
              <span className="text-sm font-semibold text-white">ShopBot AI</span>
              <span className="text-xs text-ash">— AI Shopping Assistant</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {INTEGRATION_PRODUCTS.map((product) => (
                <motion.button
                  key={product.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => runStorefrontDemo(product)}
                  disabled={storePhase !== 'idle' && storePhase !== 'result'}
                  className={`rounded-xl p-4 border text-left transition-all ${
                    selectedProduct?.id === product.id
                      ? product.safe
                        ? 'border-cyan/40 bg-cyan/5'
                        : 'border-coral/40 bg-coral/5'
                      : 'border-slate/30 bg-steel/20 hover:border-slate/50'
                  } ${storePhase !== 'idle' && storePhase !== 'result' ? 'opacity-50 cursor-wait' : ''}`}
                >
                  <div className="text-2xl mb-2">{product.icon}</div>
                  <div className="text-sm font-medium text-white mb-1 truncate">{product.name}</div>
                  <div className="text-xs font-mono text-smoke mb-1">${product.price}</div>
                  <div className="text-[10px] text-ash truncate">{product.vendor}</div>
                  {!product.safe && (
                    <div className="mt-2 text-[10px] text-coral/70 font-mono">{product.attackNote}</div>
                  )}
                </motion.button>
              ))}
            </div>
          </div>

          {/* Right: VetoNet Shield Panel */}
          <div className="rounded-2xl border border-slate/40 bg-obsidian/60 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate/30 flex items-center gap-2 bg-obsidian/80">
              <Shield className="w-4 h-4 text-cyan" />
              <span className="text-xs font-mono text-smoke">vetonet_shield</span>
              {storePhase === 'scanning' && (
                <span className="ml-auto text-[10px] font-mono text-cyan animate-pulse flex items-center gap-1">
                  <Activity className="w-3 h-3" /> scanning
                </span>
              )}
            </div>

            <div className="p-4 min-h-[280px]">
              {storePhase === 'idle' && !selectedProduct && (
                <div className="h-full flex flex-col items-center justify-center text-center py-8">
                  <Shield className="w-10 h-10 text-slate mb-3" strokeWidth={1} />
                  <p className="text-sm text-ash">Click a product to see VetoNet in action</p>
                </div>
              )}

              {storePhase === 'locking' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center py-8 gap-3">
                  <motion.div animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Lock className="w-8 h-8 text-cyan" />
                  </motion.div>
                  <span className="text-xs font-mono text-cyan">Locking user intent...</span>
                </motion.div>
              )}

              {storePhase === 'shopping' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center py-8 gap-3">
                  <motion.div animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity }}>
                    <Bot className="w-8 h-8 text-smoke" />
                  </motion.div>
                  <span className="text-xs font-mono text-smoke">Agent returning payload...</span>
                </motion.div>
              )}

              {(storePhase === 'scanning' || storePhase === 'result') && (
                <div className="space-y-4">
                  {selectedProduct && (
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                      <div className="rounded-lg bg-cyan/5 border border-cyan/20 p-2.5">
                        <div className="text-cyan text-[10px] mb-1">INTENT</div>
                        <div className="text-white truncate">{selectedProduct.prompt}</div>
                      </div>
                      <div className={`rounded-lg p-2.5 ${
                        selectedProduct.safe
                          ? 'bg-lime/5 border border-lime/20'
                          : 'bg-coral/5 border border-coral/20'
                      }`}>
                        <div className={`text-[10px] mb-1 ${selectedProduct.safe ? 'text-lime' : 'text-coral'}`}>PAYLOAD</div>
                        <div className="text-white truncate">{selectedProduct.name}</div>
                        <div className="text-ash">${selectedProduct.price} · {selectedProduct.vendor}</div>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-1.5">
                    {(storeResult?.result?.checks || INTEGRATION_CHECKS).map((check, i) => {
                      const isActive = i <= storeCheck
                      const passed = check.passed !== false
                      const failed = isActive && !passed
                      return (
                        <div key={check.id || i}
                          className={`rounded-lg p-2 text-center border transition-all ${
                            failed ? 'bg-coral/10 border-coral/30' :
                            isActive ? 'bg-cyan/10 border-cyan/20' :
                            'bg-steel/10 border-slate/20'
                          }`}>
                          {failed ? (
                            <XCircle className="w-4 h-4 mx-auto text-coral" />
                          ) : isActive ? (
                            <CheckCircle2 className="w-4 h-4 mx-auto text-cyan" />
                          ) : (
                            <div className="w-4 h-4 mx-auto rounded-full border border-slate/40" />
                          )}
                          <div className={`font-mono text-[9px] mt-1 truncate ${
                            failed ? 'text-coral' : isActive ? 'text-white' : 'text-ash'
                          }`}>{check.name}</div>
                        </div>
                      )
                    })}
                  </div>

                  {storePhase === 'result' && storeResult && (
                    <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                      className="text-center pt-2">
                      {storeResult.result?.approved ? (
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-lime/10 border border-lime/30">
                          <ShieldCheck className="w-5 h-5 text-lime" />
                          <span className="text-lime font-bold text-sm">APPROVED</span>
                        </div>
                      ) : (
                        <div>
                          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-coral/10 border border-coral/30 mb-3">
                            <ShieldAlert className="w-5 h-5 text-coral" />
                            <span className="text-coral font-bold text-sm">VETOED</span>
                          </div>
                          {storeResult.result?.checks?.filter(c => !c.passed).length > 0 && (
                            <div className="text-[11px] text-left space-y-1 mt-2">
                              {storeResult.result.checks.filter(c => !c.passed).map((c, i) => (
                                <div key={i} className="flex items-start gap-1.5 text-smoke">
                                  <XCircle className="w-3 h-3 text-coral mt-0.5 flex-shrink-0" />
                                  <span><span className="text-white">{c.name}:</span> {c.reason}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      <button onClick={resetStore}
                        className="mt-3 text-xs text-ash hover:text-white flex items-center gap-1 mx-auto transition-colors">
                        <RotateCcw className="w-3 h-3" /> Try another
                      </button>
                    </motion.div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* CTA Callout */}
        <div className="text-center rounded-2xl bg-gradient-to-r from-cyan/5 via-cyan/10 to-cyan/5 border border-cyan/20 p-6">
          <p className="text-white font-semibold mb-1">This entire checkout was protected by 3 lines of code.</p>
          <p className="text-smoke text-sm mb-4">Get your API key and start protecting transactions in minutes.</p>
          <Link to="/auth"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan to-cyan/80 text-void font-medium text-sm hover:shadow-lg hover:shadow-cyan/20 transition-all">
            <Rocket className="w-4 h-4" />
            Get Your API Key
            <ArrowRight className="w-4 h-4" />
          </Link>
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
                <span className="text-3xl font-bold text-lime">Free</span>
              </div>
              <div className="text-cyan text-sm">During early access</div>
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
