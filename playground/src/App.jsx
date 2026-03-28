import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Bot, User, Lock, Play, RotateCcw, Swords, Target, Trophy, Skull, Unlock, ChevronDown, ChevronUp } from 'lucide-react'
import './index.css'

// Use Railway backend in production, local in development
const API_BASE = import.meta.env.VITE_API_URL || 'https://web-production-fec907.up.railway.app/api'

const SECURITY_CHECKS = [
  { id: 'price', name: 'Price Limit', desc: 'Total ≤ max allowed' },
  { id: 'quantity', name: 'Quantity Match', desc: 'Correct amount' },
  { id: 'category', name: 'Category Verify', desc: 'Right product type' },
  { id: 'currency', name: 'Currency Guard', desc: 'No manipulation' },
  { id: 'vendor', name: 'Vendor TLD', desc: 'Trusted domain' },
  { id: 'anomaly', name: 'Price Anomaly', desc: 'Not suspiciously cheap' },
  { id: 'fees', name: 'Hidden Fees', desc: 'No sketchy charges' },
  { id: 'subscription', name: 'Subscription Trap', desc: 'No sneaky recurring' },
  { id: 'semantic', name: 'Semantic Match', desc: 'AI intent verification' },
]

const EXAMPLE_PROMPTS = [
  '$50 Amazon Gift Card',
  'Buy me a Nintendo Switch for under $300',
  'Order 2 large pizzas from Dominos, max $40',
  'Get a monthly Netflix subscription',
]

// Helper function for relative time formatting
function formatRelativeTime(timestamp) {
  const now = Date.now()
  const diff = now - new Date(timestamp).getTime()

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return `${seconds} sec ago`
  if (minutes < 60) return `${minutes} min ago`
  if (hours < 24) return `${hours} hr ago`
  return `${days} day${days > 1 ? 's' : ''} ago`
}

// AttackFeed Component - Real-time scrolling feed of attacks
function AttackFeed() {
  const [attacks, setAttacks] = useState([])
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLive, setIsLive] = useState(true)

  // Fetch attacks from API
  const fetchAttacks = async () => {
    try {
      const res = await fetch(`${API_BASE}/feed`)
      if (res.ok) {
        const data = await res.json()
        // Map API response to component format
        const mapped = (data.attacks || []).slice(0, 10).map(a => ({
          ...a,
          blocked: !a.bypassed,
          reason: a.blocked_by
        }))
        setAttacks(mapped)
        setIsLive(true)
      }
    } catch (e) {
      setIsLive(false)
    }
  }

  // Fetch on mount and every 5 seconds
  useEffect(() => {
    fetchAttacks()
    const interval = setInterval(fetchAttacks, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative z-10 px-6 mb-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          className="glass-card rounded-xl overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b border-slate/30 cursor-pointer md:cursor-default"
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            <div className="flex items-center gap-3">
              <h3 className="font-mono text-sm font-semibold text-white tracking-wide">
                LIVE ATTACK FEED
              </h3>
              <div className="flex items-center gap-2">
                <motion.div
                  className={`w-2 h-2 rounded-full ${isLive ? 'bg-lime' : 'bg-coral'}`}
                  animate={{ opacity: isLive ? [1, 0.4, 1] : 1 }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <span className={`font-mono text-xs ${isLive ? 'text-lime' : 'text-coral'}`}>
                  {isLive ? 'LIVE' : 'OFFLINE'}
                </span>
              </div>
            </div>
            {/* Mobile collapse toggle */}
            <button className="md:hidden text-smoke hover:text-white transition-colors">
              {isCollapsed ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
            </button>
          </div>

          {/* Feed Content */}
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="max-h-64 overflow-y-auto p-2 space-y-2">
                  {attacks.length === 0 ? (
                    <div className="text-center py-8 text-ash font-mono text-sm">
                      No attacks recorded yet. Run a demo to see activity.
                    </div>
                  ) : (
                    <AnimatePresence mode="popLayout">
                      {attacks.map((attack, index) => (
                        <motion.div
                          key={attack.id || `${attack.timestamp}-${index}`}
                          initial={{ opacity: 0, x: -20, y: -10 }}
                          animate={{ opacity: 1, x: 0, y: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          transition={{ duration: 0.3, delay: index * 0.05 }}
                          className={`rounded-lg p-3 border ${
                            attack.blocked
                              ? 'bg-cyan/5 border-cyan/20'
                              : 'bg-coral/5 border-coral/20'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className={`mt-0.5 ${attack.blocked ? 'text-cyan' : 'text-coral'}`}>
                              {attack.blocked ? (
                                <Shield className="w-4 h-4" />
                              ) : (
                                <Unlock className="w-4 h-4" />
                              )}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              {/* Prompt */}
                              <div className="text-white text-sm truncate mb-1 font-mono">
                                {attack.prompt || 'Unknown prompt'}
                              </div>

                              {/* Details row */}
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono">
                                {/* Reason */}
                                <span className={attack.blocked ? 'text-cyan' : 'text-coral'}>
                                  {attack.blocked
                                    ? attack.reason || 'Blocked'
                                    : 'All checks passed'}
                                </span>

                                {/* Vendor */}
                                {attack.vendor && (
                                  <span className="text-ash">
                                    {attack.vendor}
                                  </span>
                                )}

                                {/* Time */}
                                <span className="text-ash ml-auto">
                                  {formatRelativeTime(attack.timestamp)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  )
}

function App() {
  const [gameMode, setGameMode] = useState('demo') // 'demo' or 'redteam'
  const [prompt, setPrompt] = useState('$50 Amazon Gift Card')
  const [mode, setMode] = useState('honest')
  const [phase, setPhase] = useState('idle')
  const [currentCheck, setCurrentCheck] = useState(-1)
  const [result, setResult] = useState(null)
  const [stats, setStats] = useState({ total_attempts: 0, blocked: 0, bypassed: 0, bypass_rate: 0 })
  const [error, setError] = useState(null)
  const [useApi, setUseApi] = useState(true)

  // Red team attack payload
  const [attackPayload, setAttackPayload] = useState({
    item_description: '',
    unit_price: '',
    quantity: '1',
    vendor: '',
    currency: 'USD',
    is_recurring: false,
    fees: []
  })
  const [newFee, setNewFee] = useState({ name: '', amount: '' })

  // Fetch stats on load
  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      // API not available, that's okay
    }
  }

  const runDemo = async () => {
    setPhase('locking')
    setResult(null)
    setCurrentCheck(-1)
    setError(null)

    try {
      // Try API first
      if (useApi) {
        const res = await fetch(`${API_BASE}/demo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, mode })
        })

        if (res.ok) {
          const data = await res.json()
          await animateResult(data)
          fetchStats()
          return
        }
      }
    } catch (e) {
      console.log('API unavailable, using mock data')
      setUseApi(false)
    }

    // Fallback to mock
    await animateMock()
  }

  const runRedTeam = async () => {
    setPhase('locking')
    setResult(null)
    setCurrentCheck(-1)
    setError(null)

    // Validate payload
    if (!attackPayload.item_description || !attackPayload.unit_price || !attackPayload.vendor) {
      setError('Fill in all required fields: Item, Price, and Vendor')
      setPhase('idle')
      return
    }

    try {
      const res = await fetch(`${API_BASE}/redteam`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          payload: {
            ...attackPayload,
            unit_price: parseFloat(attackPayload.unit_price),
            quantity: parseInt(attackPayload.quantity),
            fees: attackPayload.fees.map(f => ({ name: f.name, amount: parseFloat(f.amount) }))
          }
        })
      })

      if (res.ok) {
        const data = await res.json()
        await animateResult(data)
        fetchStats()
        return
      } else {
        setError('API error. Make sure the backend is running: python api.py')
        setPhase('idle')
      }
    } catch (e) {
      setError('Cannot connect to API. Run: python api.py')
      setPhase('idle')
    }
  }

  const animateResult = async (data) => {
    // Animate phases
    await sleep(800)
    setPhase('shopping')
    await sleep(1000)
    setPhase('scanning')

    // Animate through checks
    const checks = data.result.checks
    for (let i = 0; i < checks.length; i++) {
      setCurrentCheck(i)
      await sleep(250)
      if (!checks[i].passed) {
        await sleep(300)
        break
      }
    }

    await sleep(400)
    setPhase('result')
    setResult(data)
  }

  const animateMock = async () => {
    // Mock fallback when API unavailable
    await sleep(1200)
    setPhase('shopping')
    await sleep(1500)
    setPhase('scanning')

    const mockChecks = SECURITY_CHECKS.map((c, i) => ({
      ...c,
      passed: mode === 'honest' || i > 3,
      reason: mode === 'compromised' && i <= 3 ? 'Mock violation' : null
    }))

    for (let i = 0; i < mockChecks.length; i++) {
      setCurrentCheck(i)
      await sleep(300)
      if (!mockChecks[i].passed) break
    }

    await sleep(500)
    setPhase('result')
    setResult({
      intent: { item_category: 'gift_card', max_price: 50, quantity: 1, is_recurring: false },
      payload: {
        item_description: mode === 'honest' ? 'Amazon Gift Card $50' : 'Steam Card (HACKED)',
        unit_price: mode === 'honest' ? 50 : 49.99,
        vendor: mode === 'honest' ? 'amazon.com' : 'scam.xyz',
        fees: mode === 'honest' ? [] : [{ name: 'Hidden Fee', amount: 9.99 }],
        is_recurring: mode === 'compromised'
      },
      result: {
        approved: mode === 'honest',
        checks: mockChecks,
        message: mode === 'honest' ? 'Approved' : 'Vetoed'
      },
      bypassed: false
    })
  }

  const reset = () => {
    setPhase('idle')
    setResult(null)
    setCurrentCheck(-1)
    setError(null)
  }

  const addFee = () => {
    if (newFee.name && newFee.amount) {
      setAttackPayload({
        ...attackPayload,
        fees: [...attackPayload.fees, { ...newFee }]
      })
      setNewFee({ name: '', amount: '' })
    }
  }

  return (
    <div className="min-h-screen bg-void grid-bg relative noise">
      {/* Hero Section */}
      <header className="relative z-10 pt-12 pb-8 px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-4xl mx-auto text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <motion.div
              className="relative"
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity }}
            >
              <Shield className="w-14 h-14 text-cyan" />
              <div className="absolute inset-0 bg-cyan/20 blur-xl rounded-full" />
            </motion.div>
          </div>

          <h1 className="font-display text-4xl md:text-6xl font-bold mb-3 tracking-tight">
            <span className="text-white">Veto</span>
            <span className="gradient-text">Net</span>
          </h1>

          <p className="text-lg md:text-xl text-smoke font-light">
            Semantic Firewall for AI Agents
          </p>
        </motion.div>
      </header>

      {/* Stats Bar */}
      <div className="relative z-10 px-6 mb-6">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card rounded-xl p-4 flex justify-center gap-8 text-center">
            <div>
              <div className="text-2xl font-bold text-white">{stats.total_attempts}</div>
              <div className="text-xs text-ash font-mono">Total Attempts</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-lime">{stats.blocked}</div>
              <div className="text-xs text-ash font-mono">Blocked</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-coral">{stats.bypassed}</div>
              <div className="text-xs text-ash font-mono">Bypassed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-amber">{stats.bypass_rate}%</div>
              <div className="text-xs text-ash font-mono">Bypass Rate</div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Attack Feed */}
      <AttackFeed />

      {/* Game Mode Toggle */}
      <div className="relative z-10 px-6 mb-6">
        <div className="flex justify-center">
          <div className="glass-card rounded-full p-1 flex gap-1">
            <button
              onClick={() => { setGameMode('demo'); reset(); }}
              className={`px-6 py-3 rounded-full font-mono text-sm transition-all flex items-center gap-2 ${
                gameMode === 'demo'
                  ? 'bg-cyan/20 text-cyan border border-cyan/30'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <Play className="w-4 h-4" />
              Demo Mode
            </button>
            <button
              onClick={() => { setGameMode('redteam'); reset(); }}
              className={`px-6 py-3 rounded-full font-mono text-sm transition-all flex items-center gap-2 ${
                gameMode === 'redteam'
                  ? 'bg-coral/20 text-coral border border-coral/30'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <Swords className="w-4 h-4" />
              Red Team Challenge
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="relative z-10 px-6 pb-20">
        <div className="max-w-6xl mx-auto">
          {gameMode === 'demo' ? (
            <DemoMode
              prompt={prompt}
              setPrompt={setPrompt}
              mode={mode}
              setMode={setMode}
              phase={phase}
              currentCheck={currentCheck}
              result={result}
              runDemo={runDemo}
              reset={reset}
              error={error}
            />
          ) : (
            <RedTeamMode
              prompt={prompt}
              setPrompt={setPrompt}
              attackPayload={attackPayload}
              setAttackPayload={setAttackPayload}
              newFee={newFee}
              setNewFee={setNewFee}
              addFee={addFee}
              phase={phase}
              currentCheck={currentCheck}
              result={result}
              runRedTeam={runRedTeam}
              reset={reset}
              error={error}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate/30 py-6 px-6">
        <div className="max-w-4xl mx-auto text-center text-ash text-sm">
          <p>VetoNet — Semantic Firewall for AI Agent Transactions</p>
        </div>
      </footer>
    </div>
  )
}

function DemoMode({ prompt, setPrompt, mode, setMode, phase, currentCheck, result, runDemo, reset, error }) {
  return (
    <>
      {/* Mode Toggle */}
      <div className="flex justify-center mb-6">
        <div className="glass-card rounded-full p-1 flex gap-1">
          <button
            onClick={() => { setMode('honest'); reset(); }}
            className={`px-5 py-2 rounded-full font-mono text-sm transition-all ${
              mode === 'honest'
                ? 'bg-lime/20 text-lime border border-lime/30'
                : 'text-smoke hover:text-white'
            }`}
          >
            <Bot className="w-4 h-4 inline mr-2" />
            Honest Agent
          </button>
          <button
            onClick={() => { setMode('compromised'); reset(); }}
            className={`px-5 py-2 rounded-full font-mono text-sm transition-all ${
              mode === 'compromised'
                ? 'bg-coral/20 text-coral border border-coral/30'
                : 'text-smoke hover:text-white'
            }`}
          >
            <AlertTriangle className="w-4 h-4 inline mr-2" />
            Compromised Agent
          </button>
        </div>
      </div>

      {/* Prompt Input */}
      <div className="max-w-2xl mx-auto mb-6">
        <div className="glass-card rounded-xl p-1">
          <div className="flex items-center gap-3 px-4 py-3">
            <User className="w-5 h-5 text-cyan" />
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your purchase intent..."
              className="flex-1 bg-transparent outline-none text-white font-display placeholder:text-ash"
            />
            <button
              onClick={phase === 'idle' ? runDemo : reset}
              disabled={phase !== 'idle' && phase !== 'result'}
              className={`px-5 py-2 rounded-lg font-mono text-sm font-medium transition-all ${
                phase === 'idle' || phase === 'result'
                  ? 'bg-cyan text-void hover:bg-cyan/90'
                  : 'bg-slate text-ash cursor-not-allowed'
              }`}
            >
              {phase === 'idle' ? 'Run' : phase === 'result' ? 'Reset' : '...'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 text-coral text-sm text-center">{error}</div>
        )}

        <div className="flex flex-wrap gap-2 mt-3 justify-center">
          {EXAMPLE_PROMPTS.map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex)}
              className="px-3 py-1 rounded-md bg-steel/50 text-smoke text-xs hover:bg-steel hover:text-white transition-all font-mono"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Results Display */}
      <ResultsDisplay phase={phase} currentCheck={currentCheck} result={result} mode={mode} />
    </>
  )
}

function RedTeamMode({ prompt, setPrompt, attackPayload, setAttackPayload, newFee, setNewFee, addFee, phase, currentCheck, result, runRedTeam, reset, error }) {
  return (
    <>
      {/* Challenge Header */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-coral/20 border border-coral/30 text-coral font-mono text-sm mb-3">
          <Target className="w-4 h-4" />
          CHALLENGE: Bypass VetoNet
        </div>
        <p className="text-smoke text-sm max-w-xl mx-auto">
          Craft a malicious payload that tricks VetoNet into approving a transaction that doesn't match the user's intent.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Left: User Intent */}
        <div className="glass-card rounded-xl p-4">
          <h3 className="text-cyan font-mono text-sm mb-3 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            USER'S ORIGINAL INTENT
          </h3>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="What the user actually wanted..."
            className="w-full bg-obsidian border border-slate rounded-lg px-4 py-3 text-white font-display placeholder:text-ash outline-none focus:border-cyan"
          />
          <p className="text-ash text-xs mt-2">
            VetoNet will extract and lock this intent. Your attack payload must try to drift from it.
          </p>
        </div>

        {/* Right: Attack Payload */}
        <div className="glass-card rounded-xl p-4">
          <h3 className="text-coral font-mono text-sm mb-3 flex items-center gap-2">
            <Skull className="w-4 h-4" />
            YOUR ATTACK PAYLOAD
          </h3>
          <div className="space-y-3">
            <input
              type="text"
              value={attackPayload.item_description}
              onChange={(e) => setAttackPayload({ ...attackPayload, item_description: e.target.value })}
              placeholder="Item description (e.g., 'Steam Gift Card $500')"
              className="w-full bg-obsidian border border-slate rounded-lg px-3 py-2 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral"
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                type="number"
                value={attackPayload.unit_price}
                onChange={(e) => setAttackPayload({ ...attackPayload, unit_price: e.target.value })}
                placeholder="Price"
                className="bg-obsidian border border-slate rounded-lg px-3 py-2 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral"
              />
              <input
                type="text"
                value={attackPayload.vendor}
                onChange={(e) => setAttackPayload({ ...attackPayload, vendor: e.target.value })}
                placeholder="Vendor (e.g., scam.xyz)"
                className="bg-obsidian border border-slate rounded-lg px-3 py-2 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral"
              />
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-smoke cursor-pointer">
                <input
                  type="checkbox"
                  checked={attackPayload.is_recurring}
                  onChange={(e) => setAttackPayload({ ...attackPayload, is_recurring: e.target.checked })}
                  className="accent-coral"
                />
                Recurring charge
              </label>
            </div>

            {/* Hidden Fees */}
            <div className="border-t border-slate pt-3">
              <div className="text-xs text-ash mb-2">Hidden Fees:</div>
              {attackPayload.fees.map((fee, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-coral mb-1">
                  <span>{fee.name}: ${fee.amount}</span>
                  <button
                    onClick={() => setAttackPayload({
                      ...attackPayload,
                      fees: attackPayload.fees.filter((_, j) => j !== i)
                    })}
                    className="text-ash hover:text-coral"
                  >×</button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newFee.name}
                  onChange={(e) => setNewFee({ ...newFee, name: e.target.value })}
                  placeholder="Fee name"
                  className="flex-1 bg-obsidian border border-slate rounded px-2 py-1 text-white text-xs font-mono placeholder:text-ash outline-none"
                />
                <input
                  type="number"
                  value={newFee.amount}
                  onChange={(e) => setNewFee({ ...newFee, amount: e.target.value })}
                  placeholder="$"
                  className="w-16 bg-obsidian border border-slate rounded px-2 py-1 text-white text-xs font-mono placeholder:text-ash outline-none"
                />
                <button
                  onClick={addFee}
                  className="px-2 py-1 bg-coral/20 text-coral rounded text-xs hover:bg-coral/30"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="text-coral text-sm text-center mb-4">{error}</div>
      )}

      {/* Launch Attack Button */}
      <div className="text-center mb-6">
        <button
          onClick={phase === 'idle' ? runRedTeam : reset}
          disabled={phase !== 'idle' && phase !== 'result'}
          className={`px-8 py-3 rounded-xl font-mono font-medium transition-all ${
            phase === 'idle' || phase === 'result'
              ? 'bg-coral text-white hover:bg-coral/90 glow-coral'
              : 'bg-slate text-ash cursor-not-allowed'
          }`}
        >
          {phase === 'idle' ? (
            <><Swords className="w-5 h-5 inline mr-2" />Launch Attack</>
          ) : phase === 'result' ? (
            <><RotateCcw className="w-5 h-5 inline mr-2" />Try Again</>
          ) : (
            'Attacking...'
          )}
        </button>
      </div>

      {/* Results */}
      <ResultsDisplay phase={phase} currentCheck={currentCheck} result={result} isRedTeam={true} />

      {/* Victory/Defeat Banner */}
      <AnimatePresence>
        {phase === 'result' && result && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-6 text-center"
          >
            {result.bypassed || result.result?.approved ? (
              <div className="inline-flex flex-col items-center gap-2 px-6 py-4 rounded-xl bg-amber/20 border border-amber/50">
                <div className="flex items-center gap-3">
                  <Trophy className="w-6 h-6 text-amber" />
                  <span className="text-amber font-bold text-lg">TRANSACTION APPROVED</span>
                </div>
                <span className="text-smoke text-sm">Your payload matched the intent - try crafting a malicious one!</span>
                <span className="text-ash text-xs">Change the item, add fees, use scam vendor, or enable recurring</span>
              </div>
            ) : (
              <div className="inline-flex items-center gap-3 px-6 py-3 rounded-xl bg-lime/20 border border-lime/50">
                <ShieldCheck className="w-6 h-6 text-lime" />
                <span className="text-lime font-bold text-lg">ATTACK BLOCKED</span>
                <span className="text-smoke text-sm">VetoNet caught the drift!</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function ResultsDisplay({ phase, currentCheck, result, mode, isRedTeam }) {
  if (phase === 'idle') return null

  return (
    <>
      {/* Three Column Flow */}
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        {/* Intent */}
        <motion.div
          className={`terminal ${phase !== 'idle' ? 'glow-cyan' : ''}`}
          animate={{ opacity: phase === 'idle' ? 0.5 : 1 }}
        >
          <div className="terminal-header">
            <div className="terminal-dot bg-coral" />
            <div className="terminal-dot bg-amber" />
            <div className="terminal-dot bg-lime" />
            <span className="ml-2 text-smoke text-xs">intent.lock</span>
          </div>
          <div className="p-3 min-h-[140px]">
            <div className="text-cyan text-xs mb-2">$ lock --intent</div>
            {result?.intent && (
              <div className="text-xs space-y-1">
                <div><span className="text-smoke">category:</span> <span className="text-white">{result.intent.item_category}</span></div>
                <div><span className="text-smoke">max:</span> <span className="text-white">${result.intent.max_price}</span></div>
                <div><span className="text-smoke">qty:</span> <span className="text-white">{result.intent.quantity}</span></div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Payload */}
        <motion.div
          className={`terminal ${phase === 'shopping' || phase === 'scanning' || phase === 'result' ? (isRedTeam ? 'glow-coral' : mode === 'compromised' ? 'glow-coral' : 'glow-lime') : ''}`}
          animate={{ opacity: ['idle', 'locking'].includes(phase) ? 0.5 : 1 }}
        >
          <div className="terminal-header">
            <div className="terminal-dot bg-coral" />
            <div className="terminal-dot bg-amber" />
            <div className="terminal-dot bg-lime" />
            <span className="ml-2 text-smoke text-xs">payload</span>
          </div>
          <div className="p-3 min-h-[140px]">
            {result?.payload && (
              <div className="text-xs space-y-1">
                <div className="text-white truncate">{result.payload.item_description}</div>
                <div><span className="text-smoke">vendor:</span> <span className="text-white">{result.payload.vendor}</span></div>
                <div><span className="text-smoke">price:</span> <span className="text-white">${result.payload.unit_price}</span></div>
                {result.payload.fees?.length > 0 && (
                  <div className="text-coral">+fees: ${result.payload.fees.reduce((a, f) => a + f.amount, 0)}</div>
                )}
              </div>
            )}
          </div>
        </motion.div>

        {/* Decision */}
        <motion.div
          className={`terminal ${phase === 'result' ? (result?.result?.approved ? 'glow-lime' : 'glow-coral') : ''}`}
          animate={{ opacity: ['idle', 'locking', 'shopping'].includes(phase) ? 0.5 : 1 }}
        >
          <div className="terminal-header">
            <div className="terminal-dot bg-coral" />
            <div className="terminal-dot bg-amber" />
            <div className="terminal-dot bg-lime" />
            <span className="ml-2 text-smoke text-xs">vetonet</span>
          </div>
          <div className="p-3 min-h-[140px] flex items-center justify-center">
            {phase === 'result' && result && (
              <motion.div
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                className="text-center"
              >
                {result.result?.approved ? (
                  <>
                    <ShieldCheck className="w-10 h-10 mx-auto text-lime mb-1" />
                    <div className="text-lime font-bold">APPROVED</div>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-10 h-10 mx-auto text-coral mb-1" />
                    <div className="text-coral font-bold">VETOED</div>
                  </>
                )}
              </motion.div>
            )}
            {phase === 'scanning' && (
              <div className="text-cyan text-xs">Scanning...</div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Security Checks */}
      {(phase === 'scanning' || phase === 'result') && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
            {(result?.result?.checks || SECURITY_CHECKS).map((check, i) => {
              const isActive = i <= currentCheck
              const passed = check.passed !== false
              const failed = isActive && !passed

              return (
                <motion.div
                  key={check.id || i}
                  animate={{ opacity: isActive ? 1 : 0.3 }}
                  className={`rounded-lg p-2 text-center ${
                    failed ? 'bg-coral/20 border border-coral/50' :
                    isActive ? 'bg-cyan/10 border border-cyan/30' :
                    'bg-steel/30 border border-slate/30'
                  }`}
                >
                  {failed ? (
                    <XCircle className="w-4 h-4 mx-auto text-coral" />
                  ) : isActive ? (
                    <CheckCircle2 className="w-4 h-4 mx-auto text-cyan" />
                  ) : (
                    <div className="w-4 h-4 mx-auto rounded-full border border-slate" />
                  )}
                  <div className={`font-mono text-[10px] mt-1 ${failed ? 'text-coral' : isActive ? 'text-white' : 'text-ash'}`}>
                    {check.name}
                  </div>
                </motion.div>
              )
            })}
          </div>

          {/* Failed reasons */}
          {phase === 'result' && result?.result?.checks?.some(c => !c.passed) && (
            <div className="mt-4 glass-card rounded-xl p-4 border border-coral/30 max-w-2xl mx-auto">
              <h4 className="text-coral font-mono text-xs mb-2 flex items-center gap-2">
                <AlertTriangle className="w-3 h-3" />
                VIOLATIONS
              </h4>
              <div className="space-y-1">
                {result.result.checks.filter(c => !c.passed).map((c, i) => (
                  <div key={i} className="text-xs flex items-start gap-2">
                    <XCircle className="w-3 h-3 text-coral mt-0.5 flex-shrink-0" />
                    <span className="text-white">{c.name}:</span>
                    <span className="text-smoke">{c.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </>
  )
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export default App
