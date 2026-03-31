import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion'
import {
  Shield, ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, XCircle,
  Bot, User, Lock, Play, RotateCcw, Swords, Target, Trophy, Skull, Unlock,
  ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, AlertCircle, Zap, Eye,
  TrendingUp, BarChart3, Activity, Send, Sparkles, ArrowRight, ExternalLink,
  DollarSign, CreditCard, Ban, CircleDollarSign
} from 'lucide-react'
import { createClient } from '@supabase/supabase-js'
import './index.css'

// API Configuration
const API_BASE = import.meta.env.VITE_API_URL || 'https://web-production-fec907.up.railway.app/api'

// Supabase Configuration (anon key is safe for client-side)
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://tihvfpvgpdmoqjhdsyge.supabase.co'
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_l1AhHLPUeoeNgckmjkfRjA_URBjkeXH'
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

const SECURITY_CHECKS = [
  { id: 'price', name: 'Price Limit', desc: 'Total within bounds' },
  { id: 'quantity', name: 'Quantity', desc: 'Correct amount' },
  { id: 'category', name: 'Category', desc: 'Right product' },
  { id: 'currency', name: 'Currency', desc: 'No manipulation' },
  { id: 'vendor', name: 'Vendor', desc: 'Trusted domain' },
  { id: 'anomaly', name: 'Anomaly', desc: 'Price check' },
  { id: 'fees', name: 'Fees', desc: 'No hidden costs' },
  { id: 'subscription', name: 'Recurring', desc: 'No sneaky billing' },
  { id: 'semantic', name: 'Semantic', desc: 'AI verification' },
]

const EXAMPLE_PROMPTS = [
  { text: '$50 Amazon Gift Card', category: 'gift_card' },
  { text: 'Nintendo Switch under $300', category: 'electronics' },
  { text: '2 large pizzas from Dominos, max $40', category: 'food' },
  { text: 'Monthly Netflix subscription', category: 'subscription' },
]

// Attack vector display names and colors
const ATTACK_VECTOR_INFO = {
  vendor_spoofing: { name: 'Vendor Spoofing', color: 'coral', icon: 'store' },
  hidden_fees: { name: 'Hidden Fees', color: 'amber', icon: 'dollar' },
  price_manipulation: { name: 'Price Manipulation', color: 'coral', icon: 'trending' },
  quantity_manipulation: { name: 'Quantity Manipulation', color: 'amber', icon: 'hash' },
  category_drift: { name: 'Category Drift', color: 'violet', icon: 'shuffle' },
  currency_manipulation: { name: 'Currency Manipulation', color: 'coral', icon: 'currency' },
  subscription_injection: { name: 'Subscription Injection', color: 'coral', icon: 'repeat' },
  combo_attack: { name: 'Combo Attack', color: 'coral', icon: 'layers' },
  random_combo: { name: 'Random Combo', color: 'coral', icon: 'shuffle' },
  semantic_attack: { name: 'Semantic Attack', color: 'violet', icon: 'brain' },
}

// Staggered animation variants
const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.4, 0.25, 1] } }
}

// Relative time formatter
function formatRelativeTime(timestamp) {
  if (!timestamp) return 'just now'
  let ts = timestamp
  if (!ts.endsWith('Z') && !ts.includes('+')) ts = ts + 'Z'
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 0 || isNaN(diff)) return 'just now'
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  if (seconds < 60) return `${seconds}s ago`
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

// =============================================================================
// EXAMPLE SCENARIOS - Pre-loaded intent examples users can test against
// =============================================================================
function FamousAttacks({ onSelectAttack, isExpanded, setIsExpanded }) {
  const [attacks, setAttacks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFamousAttacks()
  }, [])

  const fetchFamousAttacks = async () => {
    try {
      // Fetch interesting attacks: high-value attempts, various vectors, some bypasses
      const { data, error } = await supabase
        .from('attacks')
        .select('id, prompt, attack_vector, payload, verdict, blocked_by')
        .not('attack_vector', 'is', null)
        .not('prompt', 'is', null)
        .order('created_at', { ascending: false })
        .limit(100)

      if (error) throw error

      // Filter and dedupe to get interesting diverse examples
      const seen = new Set()
      const interesting = []

      // Prioritize: bypasses first, then high-value, then variety of vectors
      const sorted = [...(data || [])].sort((a, b) => {
        // Bypasses are most interesting
        if (a.verdict === 'approved' && b.verdict !== 'approved') return -1
        if (b.verdict === 'approved' && a.verdict !== 'approved') return 1
        // Then sort by payload value if available
        const aPrice = a.payload?.unit_price || 0
        const bPrice = b.payload?.unit_price || 0
        return bPrice - aPrice
      })

      for (const attack of sorted) {
        // Skip if we've seen this vector already (for variety)
        const key = `${attack.attack_vector}-${attack.prompt?.substring(0, 30)}`
        if (seen.has(key)) continue
        seen.add(key)

        // Skip very short or empty prompts
        if (!attack.prompt || attack.prompt.length < 10) continue

        interesting.push({
          id: attack.id,
          prompt: attack.prompt,
          vector: attack.attack_vector,
          payload: attack.payload,
          bypassed: attack.verdict === 'approved',
          blockedBy: attack.blocked_by
        })

        // Get max 8 examples
        if (interesting.length >= 8) break
      }

      setAttacks(interesting)
    } catch (e) {
      console.error('Failed to fetch famous attacks:', e)
      setAttacks([])
    }
    setLoading(false)
  }

  const getVectorInfo = (vector) => {
    return ATTACK_VECTOR_INFO[vector] || { name: vector?.replace(/_/g, ' ') || 'Unknown', color: 'ash', icon: 'zap' }
  }

  if (loading) {
    return (
      <div className="mt-6 text-center">
        <div className="text-ash text-sm">Loading attack examples...</div>
      </div>
    )
  }

  if (attacks.length === 0) return null

  return (
    <div className="mt-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-center gap-2 text-sm text-smoke hover:text-white transition-colors mb-3"
      >
        <Swords className="w-4 h-4 text-coral" />
        <span className="font-medium">Example Scenarios</span>
        <span className="text-xs text-ash">({attacks.length} examples)</span>
        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="grid gap-2 max-h-64 overflow-y-auto pr-1">
              {attacks.map((attack, i) => {
                const info = getVectorInfo(attack.vector)
                return (
                  <motion.button
                    key={attack.id || i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => onSelectAttack(attack)}
                    className="w-full text-left px-4 py-3 rounded-xl bg-steel/20 border border-slate/30 hover:border-coral/40 hover:bg-steel/30 transition-all group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        attack.bypassed ? 'bg-coral/20 text-coral' : 'bg-cyan/20 text-cyan'
                      }`}>
                        {attack.bypassed ? <Unlock className="w-3.5 h-3.5" /> : <Shield className="w-3.5 h-3.5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white truncate font-mono group-hover:text-coral transition-colors">
                          {attack.prompt}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full bg-${info.color}/10 text-${info.color} border border-${info.color}/20`}>
                            {info.name}
                          </span>
                          {attack.bypassed && (
                            <span className="text-xs text-coral font-medium">BYPASSED</span>
                          )}
                          {attack.payload?.unit_price && (
                            <span className="text-xs text-ash">
                              ${attack.payload.unit_price}
                            </span>
                          )}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-ash group-hover:text-coral transition-colors mt-1 flex-shrink-0" />
                    </div>
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// =============================================================================
// HERO SECTION
// =============================================================================
function HeroSection({ stats }) {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] })
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0])
  const scale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95])

  return (
    <motion.header
      ref={ref}
      style={{ opacity, scale }}
      className="relative z-10 pt-16 pb-12 px-6 overflow-hidden"
    >
      {/* Gradient orbs */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cyan/10 rounded-full blur-[120px] -translate-y-1/2" />
      <div className="absolute top-20 right-1/4 w-[400px] h-[400px] bg-violet-500/10 rounded-full blur-[100px]" />

      <motion.div
        initial="hidden"
        animate="show"
        variants={stagger}
        className="max-w-5xl mx-auto text-center relative"
      >
        {/* Badge */}
        <motion.div variants={fadeUp} className="mb-6">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan/10 border border-cyan/20 text-cyan text-sm font-medium backdrop-blur-sm">
            <Sparkles className="w-4 h-4" />
            Semantic Firewall for AI Agents
          </span>
        </motion.div>

        {/* Logo + Title */}
        <motion.div variants={fadeUp} className="flex items-center justify-center gap-4 mb-6">
          <motion.div
            className="relative"
            animate={{ rotate: [0, 3, -3, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          >
            <Shield className="w-16 h-16 text-cyan" strokeWidth={1.5} />
            <div className="absolute inset-0 bg-cyan/30 blur-2xl rounded-full scale-150" />
          </motion.div>
        </motion.div>

        <motion.h1
          variants={fadeUp}
          className="font-display text-5xl md:text-7xl font-bold mb-4 tracking-tight"
        >
          <span className="text-white">Veto</span>
          <span className="bg-gradient-to-r from-cyan via-cyan to-lime bg-clip-text text-transparent">Net</span>
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="text-xl md:text-2xl text-smoke font-light max-w-2xl mx-auto mb-6 leading-relaxed"
        >
          Prevent intent drift before your AI agent
          <span className="text-white font-medium"> drains your wallet</span>
        </motion.p>

        {/* Waitlist CTA */}
        <motion.div variants={fadeUp} className="mb-8">
          <a
            href="https://tally.so/r/Y5r7b6"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-cyan to-lime text-black font-semibold hover:opacity-90 transition-opacity"
          >
            Join the Waitlist
            <ArrowRight className="w-4 h-4" />
          </a>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={fadeUp}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto"
        >
          <StatCard
            value={stats.total_attempts}
            label="Attacks Tested"
            icon={<Activity className="w-4 h-4" />}
            color="white"
          />
          <StatCard
            value={stats.blocked}
            label="Threats Blocked"
            icon={<ShieldCheck className="w-4 h-4" />}
            color="lime"
          />
          <StatCard
            value={stats.bypassed}
            label="Bypasses"
            icon={<AlertTriangle className="w-4 h-4" />}
            color="coral"
          />
          <StatCard
            value={`${(100 - stats.bypass_rate).toFixed(1)}%`}
            label="Detection Rate"
            icon={<TrendingUp className="w-4 h-4" />}
            color="cyan"
          />
        </motion.div>
      </motion.div>
    </motion.header>
  )
}

function StatCard({ value, label, icon, color }) {
  const colorClasses = {
    white: 'text-white',
    cyan: 'text-cyan',
    lime: 'text-lime',
    coral: 'text-coral',
    amber: 'text-amber'
  }

  return (
    <div className="glass-card rounded-2xl p-4 text-center hover:border-white/10 transition-colors">
      <div className={`text-3xl md:text-4xl font-bold mb-1 ${colorClasses[color]}`}>
        {value}
      </div>
      <div className="flex items-center justify-center gap-1.5 text-ash text-xs font-mono uppercase tracking-wider">
        {icon}
        {label}
      </div>
    </div>
  )
}

// =============================================================================
// CHALLENGE BANNER SECTION - "Try to Hack It" Challenge Mode
// =============================================================================
function ChallengeBanner({ stats, onAcceptChallenge }) {
  const bypassRate = stats.total_attempts > 0
    ? ((stats.bypassed / stats.total_attempts) * 100).toFixed(1)
    : 0

  return (
    <section className="relative z-10 px-6 py-8">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative overflow-hidden rounded-3xl border-2 border-coral/40 bg-gradient-to-br from-coral/10 via-obsidian to-amber/5"
        >
          {/* Animated background pattern */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_30%_20%,rgba(255,99,99,0.3),transparent_40%)]" />
            <div className="absolute top-0 right-0 w-full h-full bg-[radial-gradient(circle_at_70%_80%,rgba(255,183,77,0.3),transparent_40%)]" />
          </div>

          <div className="relative p-8 md:p-10">
            {/* Header */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
              <div className="text-center md:text-left">
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-coral/20 border border-coral/40 text-coral text-xs font-mono uppercase tracking-wider mb-3"
                >
                  <Skull className="w-3 h-3" />
                  Open Challenge
                </motion.div>
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-2">
                  Can You <span className="text-coral">Bypass</span> Our Firewall?
                </h2>
                <p className="text-smoke text-lg">
                  Craft an attack payload that tricks VetoNet into approving a malicious transaction.
                </p>
              </div>

              {/* Trophy Icon */}
              <motion.div
                animate={{
                  rotate: [0, -5, 5, -5, 0],
                  scale: [1, 1.05, 1]
                }}
                transition={{ duration: 3, repeat: Infinity }}
                className="flex-shrink-0"
              >
                <div className="relative">
                  <Trophy className="w-20 h-20 text-amber" strokeWidth={1} />
                  <div className="absolute inset-0 bg-amber/30 blur-2xl rounded-full" />
                </div>
              </motion.div>
            </div>

            {/* Challenge Scoreboard */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="rounded-xl bg-obsidian/60 border border-slate/40 p-4 text-center backdrop-blur-sm">
                <div className="text-3xl font-bold text-white mb-1">{stats.total_attempts.toLocaleString()}</div>
                <div className="text-xs text-ash font-mono uppercase tracking-wider flex items-center justify-center gap-1">
                  <Target className="w-3 h-3" />
                  Attempts
                </div>
              </div>
              <div className="rounded-xl bg-obsidian/60 border border-lime/30 p-4 text-center backdrop-blur-sm">
                <div className="text-3xl font-bold text-lime mb-1">{stats.blocked.toLocaleString()}</div>
                <div className="text-xs text-ash font-mono uppercase tracking-wider flex items-center justify-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-lime" />
                  Blocked
                </div>
              </div>
              <div className="rounded-xl bg-obsidian/60 border border-coral/30 p-4 text-center backdrop-blur-sm">
                <div className="text-3xl font-bold text-coral mb-1">{stats.bypassed}</div>
                <div className="text-xs text-ash font-mono uppercase tracking-wider flex items-center justify-center gap-1">
                  <Unlock className="w-3 h-3 text-coral" />
                  Bypasses
                </div>
              </div>
              <div className="rounded-xl bg-obsidian/60 border border-amber/30 p-4 text-center backdrop-blur-sm">
                <div className="text-3xl font-bold text-amber mb-1">{bypassRate}%</div>
                <div className="text-xs text-ash font-mono uppercase tracking-wider flex items-center justify-center gap-1">
                  <Zap className="w-3 h-3 text-amber" />
                  Success Rate
                </div>
              </div>
            </div>

            {/* Challenge CTA */}
            <div className="text-center">
              <motion.button
                onClick={onAcceptChallenge}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-coral via-coral to-amber text-white font-bold text-lg shadow-lg shadow-coral/30 hover:shadow-xl hover:shadow-coral/40 transition-all"
              >
                <Swords className="w-6 h-6" />
                Accept the Challenge
                <ArrowRight className="w-5 h-5" />
              </motion.button>
              <p className="text-ash text-sm mt-3">
                Only <span className="text-coral font-medium">{bypassRate}%</span> of attacks have succeeded. Think you can do better?
              </p>
            </div>

            {/* Hall of Fame teaser */}
            <div className="mt-8 pt-6 border-t border-slate/30">
              <div className="flex items-center justify-center gap-2 text-sm text-smoke">
                <Trophy className="w-4 h-4 text-amber" />
                <span>Find a bypass? Your attack vector joins the leaderboard below.</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// =============================================================================
// HOW IT WORKS SECTION
// =============================================================================
function HowItWorks() {
  const steps = [
    {
      icon: <Lock className="w-6 h-6" />,
      title: "Intent Anchor",
      desc: "User's intent is cryptographically locked before the agent shops"
    },
    {
      icon: <Bot className="w-6 h-6" />,
      title: "Agent Shops",
      desc: "AI agent browses, negotiates, and selects a transaction"
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "VetoNet Intercepts",
      desc: "10 security checks + semantic AI verification"
    },
    {
      icon: <CheckCircle2 className="w-6 h-6" />,
      title: "Approve or Veto",
      desc: "Only transactions matching original intent pass through"
    }
  ]

  return (
    <section className="relative z-10 px-6 py-16">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl font-bold text-white mb-3">How It Works</h2>
          <p className="text-smoke">Four steps between your intent and your money</p>
        </motion.div>

        <div className="grid md:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative"
            >
              {/* Connector line */}
              {i < steps.length - 1 && (
                <div className="hidden md:block absolute top-8 left-[60%] w-full h-px bg-gradient-to-r from-slate to-transparent" />
              )}

              <div className="glass-card rounded-2xl p-6 h-full hover:border-cyan/30 transition-all group">
                <div className="w-12 h-12 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center text-cyan mb-4 group-hover:scale-110 transition-transform">
                  {step.icon}
                </div>
                <div className="text-xs text-cyan font-mono mb-2">STEP {i + 1}</div>
                <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-smoke leading-relaxed">{step.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// =============================================================================
// BEFORE/AFTER COMPARISON
// =============================================================================
function BeforeAfterComparison() {
  const [showAfter, setShowAfter] = useState(false)

  const scenario = {
    userIntent: "$50 Amazon Gift Card",
    withoutVetoNet: {
      description: "Agent gets prompt-injected by malicious product listing",
      item: "Amazon Gift Card $500 (SPECIAL DEAL!!!)",
      price: 500,
      vendor: "amaz0n-deals.xyz",
      fees: [{ name: "Processing", amount: 29.99 }, { name: "Service", amount: 19.99 }],
      total: 549.98,
      recurring: true,
      outcome: "User loses $549.98 + monthly charges"
    },
    withVetoNet: {
      description: "VetoNet intercepts and blocks the fraudulent transaction",
      item: "Amazon Gift Card $50",
      price: 50,
      vendor: "amazon.com",
      fees: [],
      total: 50,
      recurring: false,
      outcome: "User protected - attack blocked"
    }
  }

  return (
    <section className="relative z-10 px-6 py-16">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-10"
        >
          <h2 className="text-3xl font-bold text-white mb-3">See the Difference</h2>
          <p className="text-smoke max-w-xl mx-auto">
            User asks for a <span className="text-cyan font-medium">$50 gift card</span>.
            Watch what happens when the AI agent gets manipulated.
          </p>
        </motion.div>

        {/* Toggle Switch */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex justify-center mb-8"
        >
          <div className="inline-flex p-1.5 rounded-2xl bg-steel/50 border border-slate/50 backdrop-blur-sm">
            <button
              onClick={() => setShowAfter(false)}
              className={`px-6 py-3 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${
                !showAfter
                  ? 'bg-gradient-to-r from-coral/20 to-coral/10 text-coral border border-coral/30 shadow-lg shadow-coral/10'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <Ban className="w-4 h-4" />
              Without VetoNet
            </button>
            <button
              onClick={() => setShowAfter(true)}
              className={`px-6 py-3 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${
                showAfter
                  ? 'bg-gradient-to-r from-cyan/20 to-cyan/10 text-cyan border border-cyan/30 shadow-lg shadow-cyan/10'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              With VetoNet
            </button>
          </div>
        </motion.div>

        {/* Comparison Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* User Intent Card - Always shown */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="glass-card rounded-2xl overflow-hidden border border-cyan/30"
          >
            <div className="px-5 py-4 border-b border-slate/50 bg-cyan/5 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan/10 flex items-center justify-center">
                <User className="w-5 h-5 text-cyan" />
              </div>
              <div>
                <h3 className="font-semibold text-white">User's Intent</h3>
                <p className="text-xs text-smoke">What they actually wanted</p>
              </div>
            </div>
            <div className="p-5">
              <div className="flex items-center gap-3 mb-4">
                <Lock className="w-5 h-5 text-cyan" />
                <span className="text-lg font-medium text-white">{scenario.userIntent}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-steel/30 rounded-xl p-3">
                  <div className="text-ash text-xs mb-1">Expected Price</div>
                  <div className="text-cyan font-bold text-xl">$50</div>
                </div>
                <div className="bg-steel/30 rounded-xl p-3">
                  <div className="text-ash text-xs mb-1">Quantity</div>
                  <div className="text-white font-bold text-xl">1</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Result Card - Animated based on toggle */}
          <AnimatePresence mode="wait">
            {!showAfter ? (
              <motion.div
                key="without"
                initial={{ opacity: 0, x: 20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -20, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="glass-card rounded-2xl overflow-hidden border border-coral/30"
              >
                <div className="px-5 py-4 border-b border-coral/30 bg-coral/5 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-coral/10 flex items-center justify-center">
                    <Skull className="w-5 h-5 text-coral" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-coral">Agent Compromised</h3>
                    <p className="text-xs text-smoke">Prompt injection attack</p>
                  </div>
                </div>
                <div className="p-5">
                  <div className="text-sm text-smoke mb-4 italic">
                    "{scenario.withoutVetoNet.description}"
                  </div>

                  <div className="space-y-3 mb-4">
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Item:</span>
                      <span className="text-coral font-mono text-sm">{scenario.withoutVetoNet.item}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Price:</span>
                      <span className="text-coral font-bold">${scenario.withoutVetoNet.price}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Vendor:</span>
                      <span className="text-coral font-mono text-sm">{scenario.withoutVetoNet.vendor}</span>
                    </div>
                    {scenario.withoutVetoNet.fees.map((fee, i) => (
                      <div key={i} className="flex justify-between items-center text-coral/80">
                        <span className="text-ash text-sm">+ {fee.name}:</span>
                        <span className="font-mono text-sm">${fee.amount}</span>
                      </div>
                    ))}
                    {scenario.withoutVetoNet.recurring && (
                      <div className="flex justify-between items-center">
                        <span className="text-ash text-sm">Recurring:</span>
                        <span className="text-coral font-bold text-sm flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          MONTHLY
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-coral/20 pt-4">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-white font-medium">Total Charged:</span>
                      <span className="text-coral font-bold text-2xl">${scenario.withoutVetoNet.total}</span>
                    </div>
                    <div className="bg-coral/10 rounded-xl p-3 border border-coral/30">
                      <div className="flex items-center gap-2 text-coral">
                        <CreditCard className="w-5 h-5" />
                        <span className="font-medium text-sm">{scenario.withoutVetoNet.outcome}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="with"
                initial={{ opacity: 0, x: 20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -20, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="glass-card rounded-2xl overflow-hidden border border-lime/30"
              >
                <div className="px-5 py-4 border-b border-lime/30 bg-lime/5 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-lime/10 flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5 text-lime" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lime">Attack Blocked</h3>
                    <p className="text-xs text-smoke">VetoNet intercepted the threat</p>
                  </div>
                </div>
                <div className="p-5">
                  <div className="text-sm text-smoke mb-4 italic">
                    "{scenario.withVetoNet.description}"
                  </div>

                  {/* Attack attempt crossed out */}
                  <div className="bg-coral/5 rounded-xl p-3 mb-4 border border-coral/20 relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-full h-0.5 bg-coral/50 rotate-[-5deg]"></div>
                    </div>
                    <div className="opacity-40 space-y-1 text-sm">
                      <div className="text-coral font-mono">$500 + $49.98 fees</div>
                      <div className="text-coral font-mono">amaz0n-deals.xyz</div>
                    </div>
                    <div className="absolute top-2 right-2 bg-coral/20 rounded-lg px-2 py-1">
                      <span className="text-coral text-xs font-bold">VETOED</span>
                    </div>
                  </div>

                  <div className="space-y-3 mb-4">
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Item:</span>
                      <span className="text-lime font-mono text-sm">{scenario.withVetoNet.item}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Price:</span>
                      <span className="text-lime font-bold">${scenario.withVetoNet.price}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Vendor:</span>
                      <span className="text-lime font-mono text-sm">{scenario.withVetoNet.vendor}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ash text-sm">Hidden Fees:</span>
                      <span className="text-lime font-bold text-sm">$0</span>
                    </div>
                  </div>

                  <div className="border-t border-lime/20 pt-4">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-white font-medium">Actual Cost:</span>
                      <span className="text-lime font-bold text-2xl">${scenario.withVetoNet.total}</span>
                    </div>
                    <div className="bg-lime/10 rounded-xl p-3 border border-lime/30">
                      <div className="flex items-center gap-2 text-lime">
                        <Shield className="w-5 h-5" />
                        <span className="font-medium text-sm">{scenario.withVetoNet.outcome}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Money Saved Highlight */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="mt-8 text-center"
        >
          <div className="inline-flex items-center gap-4 px-6 py-4 rounded-2xl bg-gradient-to-r from-cyan/10 via-lime/10 to-cyan/10 border border-cyan/30">
            <div className="text-left">
              <div className="text-sm text-smoke">Money saved in this scenario</div>
              <div className="text-3xl font-bold bg-gradient-to-r from-cyan to-lime bg-clip-text text-transparent">
                $499.98
              </div>
            </div>
            <div className="w-px h-12 bg-slate/50"></div>
            <div className="text-left">
              <div className="text-sm text-smoke">Price difference</div>
              <div className="text-xl font-bold text-white">10x markup blocked</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// =============================================================================
// ATTACK LEADERBOARD
// =============================================================================
function AttackLeaderboard() {
  const [vectors, setVectors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchVectors()
    const interval = setInterval(fetchVectors, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchVectors = async () => {
    try {
      // Fetch all records from Supabase with pagination (1000 per page)
      const allData = []
      let page = 0
      const pageSize = 1000

      while (true) {
        const { data, error } = await supabase
          .from('attacks')
          .select('attack_vector, verdict')
          .not('attack_vector', 'is', null)
          .range(page * pageSize, (page + 1) * pageSize - 1)

        if (error) throw error
        if (!data || data.length === 0) break

        allData.push(...data)
        if (data.length < pageSize) break
        page++
      }

      // Aggregate by vector
      const stats = {}
      for (const attack of allData) {
        const vector = attack.attack_vector
        if (!vector) continue
        if (!stats[vector]) stats[vector] = { total: 0, blocked: 0, bypassed: 0 }
        stats[vector].total++
        if (attack.verdict === 'approved') stats[vector].bypassed++
        else stats[vector].blocked++
      }

      // Convert to sorted array
      const vectorList = Object.entries(stats)
        .map(([vector, s]) => ({ vector, ...s }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 10)

      setVectors(vectorList)
    } catch (e) {
      // Fallback to API
      try {
        const res = await fetch(`${API_BASE}/vectors`)
        if (res.ok) {
          const data = await res.json()
          setVectors(data.vectors || [])
        }
      } catch {
        setVectors([])
      }
    }
    setLoading(false)
  }

  return (
    <section className="relative z-10 px-6 py-12">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-card rounded-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-cyan" />
              <h3 className="font-semibold text-white">Attack Vector Leaderboard</h3>
            </div>
            <span className="text-xs text-ash font-mono">LIVE DATA</span>
          </div>

          {/* Table */}
          <div className="divide-y divide-slate/30">
            {loading ? (
              <div className="p-8 text-center text-ash">Loading...</div>
            ) : vectors.length === 0 ? (
              <div className="p-8 text-center text-ash">No attack data yet</div>
            ) : (
              vectors.slice(0, 5).map((v, i) => {
                const blockRate = v.total > 0 ? ((v.blocked / v.total) * 100).toFixed(1) : 0
                return (
                  <div key={i} className="px-6 py-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors">
                    {/* Rank */}
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                      i === 0 ? 'bg-amber/20 text-amber' :
                      i === 1 ? 'bg-slate/50 text-smoke' :
                      i === 2 ? 'bg-orange-900/30 text-orange-400' :
                      'bg-steel/30 text-ash'
                    }`}>
                      {i + 1}
                    </div>

                    {/* Vector name */}
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-white text-sm truncate">
                        {v.vector?.replace(/_/g, ' ') || 'Unknown'}
                      </div>
                      <div className="text-xs text-ash">{v.total} attempts</div>
                    </div>

                    {/* Progress bar */}
                    <div className="w-32 hidden md:block">
                      <div className="h-2 bg-slate/50 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${blockRate}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 1, delay: i * 0.1 }}
                          className="h-full bg-gradient-to-r from-cyan to-lime"
                        />
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="text-right">
                      <div className="text-lime text-sm font-medium">{blockRate}%</div>
                      <div className="text-xs text-ash">blocked</div>
                    </div>

                    {/* Bypasses */}
                    <div className="text-right w-16">
                      <div className={`text-sm font-medium ${v.bypassed > 0 ? 'text-coral' : 'text-ash'}`}>
                        {v.bypassed}
                      </div>
                      <div className="text-xs text-ash">bypassed</div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// =============================================================================
// LIVE FEED
// =============================================================================
function LiveFeed() {
  const [attacks, setAttacks] = useState([])
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLive, setIsLive] = useState(true)

  useEffect(() => {
    fetchAttacks()
    const interval = setInterval(fetchAttacks, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchAttacks = async () => {
    try {
      // Fetch directly from Supabase
      const { data, error } = await supabase
        .from('attacks')
        .select('id, created_at, prompt, verdict, blocked_by, attack_vector, payload')
        .order('created_at', { ascending: false })
        .limit(20)

      if (error) throw error

      const mapped = (data || []).map(a => ({
        id: a.id,
        timestamp: a.created_at,
        prompt: a.prompt,
        blocked: a.verdict === 'blocked',
        bypassed: a.verdict === 'approved',
        reason: a.blocked_by || (a.verdict === 'approved' ? 'Bypassed' : 'Security check'),
        attack_vector: a.attack_vector,
        vendor: a.payload?.vendor
      }))
      setAttacks(mapped)
      setIsLive(true)
    } catch (e) {
      // Fallback to Railway API
      try {
        const res = await fetch(`${API_BASE}/feed`)
        if (res.ok) {
          const data = await res.json()
          const mapped = (data.attacks || [])
            .slice(0, 8)
            .map(a => ({
              ...a,
              blocked: !a.bypassed,
              reason: a.blocked_by || (a.bypassed ? 'Bypassed' : 'Security check')
            }))
          setAttacks(mapped)
          setIsLive(true)
        }
      } catch {
        setIsLive(false)
      }
    }
  }

  return (
    <section className="relative z-10 px-6 py-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-card rounded-2xl overflow-hidden"
        >
          {/* Header */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="w-full px-6 py-4 border-b border-slate/50 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-cyan" />
              <h3 className="font-semibold text-white">Recent Activity</h3>
              <div className="flex items-center gap-2 ml-2">
                <motion.div
                  className={`w-2 h-2 rounded-full ${isLive ? 'bg-lime' : 'bg-coral'}`}
                  animate={{ opacity: isLive ? [1, 0.4, 1] : 1 }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <span className={`text-xs font-mono ${isLive ? 'text-lime' : 'text-coral'}`}>
                  {isLive ? 'LIVE' : 'OFFLINE'}
                </span>
              </div>
            </div>
            {isCollapsed ? <ChevronDown className="w-5 h-5 text-ash" /> : <ChevronUp className="w-5 h-5 text-ash" />}
          </button>

          {/* Feed */}
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="max-h-80 overflow-y-auto divide-y divide-slate/20">
                  {attacks.length === 0 ? (
                    <div className="p-8 text-center text-ash">
                      No activity yet. Run a demo to see attacks in real-time.
                    </div>
                  ) : (
                    attacks.map((attack, i) => (
                      <motion.div
                        key={attack.id || `${attack.timestamp}-${i}`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="px-6 py-3 flex items-center gap-4 hover:bg-white/[0.02]"
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          attack.blocked ? 'bg-cyan/10 text-cyan' : 'bg-coral/10 text-coral'
                        }`}>
                          {attack.blocked ? <Shield className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white truncate font-mono">
                            {attack.prompt || 'Unknown'}
                          </div>
                          <div className="text-xs text-ash flex items-center gap-2">
                            <span className={attack.blocked ? 'text-cyan' : 'text-coral'}>
                              {attack.reason}
                            </span>
                            {attack.vendor && <span>• {attack.vendor}</span>}
                          </div>
                        </div>
                        <div className="text-xs text-ash font-mono">
                          {formatRelativeTime(attack.timestamp)}
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </section>
  )
}

// =============================================================================
// FEEDBACK COMPONENT
// =============================================================================
function FeedbackButtons({ attackId, onFeedback }) {
  const [submitted, setSubmitted] = useState(null)
  const [loading, setLoading] = useState(false)

  const submitFeedback = async (feedback) => {
    if (submitted || loading) return
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_id: attackId, feedback })
      })
      if (res.ok) {
        setSubmitted(feedback)
        onFeedback?.(feedback)
      }
    } catch (e) {
      // Still mark as submitted for UX
      setSubmitted(feedback)
    }
    setLoading(false)
  }

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-2 text-cyan text-sm"
      >
        <CheckCircle2 className="w-4 h-4" />
        <span>Thanks for the feedback!</span>
      </motion.div>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-ash">Was this correct?</span>
      <div className="flex gap-2">
        <button
          onClick={() => submitFeedback('correct')}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg bg-lime/10 border border-lime/30 text-lime text-sm font-medium hover:bg-lime/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
        >
          <ThumbsUp className="w-3.5 h-3.5" />
          Correct
        </button>
        <button
          onClick={() => submitFeedback('false_positive')}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg bg-amber/10 border border-amber/30 text-amber text-sm font-medium hover:bg-amber/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
        >
          <AlertCircle className="w-3.5 h-3.5" />
          False Positive
        </button>
        <button
          onClick={() => submitFeedback('false_negative')}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg bg-coral/10 border border-coral/30 text-coral text-sm font-medium hover:bg-coral/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
        >
          <ThumbsDown className="w-3.5 h-3.5" />
          Missed Attack
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// MAIN PLAYGROUND
// =============================================================================
function Playground({ stats, fetchStats, playgroundRef, initialMode }) {
  const [gameMode, setGameMode] = useState(initialMode || 'demo')
  const [prompt, setPrompt] = useState('$50 Amazon Gift Card')
  const [mode, setMode] = useState('honest')
  const [phase, setPhase] = useState('idle')
  const [currentCheck, setCurrentCheck] = useState(-1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [attackId, setAttackId] = useState(null)

  // Sync with external mode changes (from ChallengeBanner)
  useEffect(() => {
    if (initialMode) {
      setGameMode(initialMode)
    }
  }, [initialMode])

  // Helper: Detect if payload actually drifted from intent (i.e., is it a real attack?)
  // TEMP: Disabled to debug black screen issue
  const detectDrift = (result) => {
    return false
  }

  // Red team payload state
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

  const runDemo = async () => {
    setPhase('locking')
    setResult(null)
    setCurrentCheck(-1)
    setError(null)
    setAttackId(null)

    try {
      const res = await fetch(`${API_BASE}/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, mode })
      })

      if (res.ok) {
        const data = await res.json()
        setAttackId(data.attack_id)
        await animateResult(data)
        fetchStats()
        return
      }
    } catch (e) {
      console.log('API unavailable, using mock')
    }

    await animateMock()
  }

  const runRedTeam = async () => {
    setPhase('locking')
    setResult(null)
    setCurrentCheck(-1)
    setError(null)
    setAttackId(null)

    if (!attackPayload.item_description || !attackPayload.unit_price || !attackPayload.vendor) {
      setError('Fill in: Item, Price, and Vendor')
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
        setAttackId(data.attack_id)
        await animateResult(data)
        fetchStats()
        return
      } else {
        setError('API error. Make sure backend is running.')
        setPhase('idle')
      }
    } catch (e) {
      setError('Cannot connect to API')
      setPhase('idle')
    }
  }

  const animateResult = async (data) => {
    await sleep(600)
    setPhase('shopping')
    await sleep(800)
    setPhase('scanning')

    const checks = data.result.checks
    for (let i = 0; i < checks.length; i++) {
      setCurrentCheck(i)
      await sleep(200)
      if (!checks[i].passed) {
        await sleep(200)
        break
      }
    }

    await sleep(300)
    setPhase('result')
    setResult(data)
  }

  const animateMock = async () => {
    await sleep(800)
    setPhase('shopping')
    await sleep(1000)
    setPhase('scanning')

    const mockChecks = SECURITY_CHECKS.map((c, i) => ({
      ...c,
      passed: mode === 'honest' || i > 3,
      reason: mode === 'compromised' && i <= 3 ? 'Mock violation' : null
    }))

    for (let i = 0; i < mockChecks.length; i++) {
      setCurrentCheck(i)
      await sleep(200)
      if (!mockChecks[i].passed) break
    }

    await sleep(300)
    setPhase('result')
    setResult({
      intent: { item_category: 'gift_card', max_price: 50, quantity: 1 },
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
    setAttackId(null)
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
    <section ref={playgroundRef} className="relative z-10 px-6 py-12">
      <div className="max-w-5xl mx-auto">
        {/* Mode Toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex justify-center mb-8"
        >
          <div className="inline-flex p-1.5 rounded-2xl bg-steel/50 border border-slate/50 backdrop-blur-sm">
            <button
              onClick={() => { setGameMode('demo'); reset(); }}
              className={`px-6 py-3 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${
                gameMode === 'demo'
                  ? 'bg-gradient-to-r from-cyan/20 to-cyan/10 text-cyan border border-cyan/30 shadow-lg shadow-cyan/10'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <Play className="w-4 h-4" />
              Demo Mode
            </button>
            <button
              onClick={() => { setGameMode('redteam'); reset(); }}
              className={`px-6 py-3 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${
                gameMode === 'redteam'
                  ? 'bg-gradient-to-r from-coral/20 to-coral/10 text-coral border border-coral/30 shadow-lg shadow-coral/10'
                  : 'text-smoke hover:text-white'
              }`}
            >
              <Swords className="w-4 h-4" />
              Red Team
            </button>
          </div>
        </motion.div>

        {/* Playground Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-card rounded-3xl p-6 md:p-8 border border-slate/50"
        >
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
              attackId={attackId}
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
              attackId={attackId}
            />
          )}
        </motion.div>
      </div>
    </section>
  )
}

// =============================================================================
// DEMO MODE
// =============================================================================
function DemoMode({ prompt, setPrompt, mode, setMode, phase, currentCheck, result, runDemo, reset, error, attackId }) {
  const [showFamousAttacks, setShowFamousAttacks] = useState(false)

  const handleSelectAttack = (attack) => {
    setPrompt(attack.prompt)
    setMode('compromised') // Switch to compromised mode for attack examples
    setShowFamousAttacks(false)
  }

  return (
    <>
      {/* Agent Mode Toggle */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex p-1 rounded-xl bg-obsidian border border-slate/50">
          <button
            onClick={() => { setMode('honest'); reset(); }}
            className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
              mode === 'honest'
                ? 'bg-lime/10 text-lime border border-lime/30'
                : 'text-smoke hover:text-white'
            }`}
          >
            <Bot className="w-4 h-4" />
            Honest Agent
          </button>
          <button
            onClick={() => { setMode('compromised'); reset(); }}
            className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
              mode === 'compromised'
                ? 'bg-coral/10 text-coral border border-coral/30'
                : 'text-smoke hover:text-white'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Compromised
          </button>
        </div>
      </div>

      {/* Prompt Input */}
      <div className="max-w-2xl mx-auto mb-6">
        <div className="relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan">
            <User className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your purchase intent..."
            className="w-full pl-12 pr-28 py-4 rounded-2xl bg-obsidian border border-slate/50 text-white placeholder:text-ash outline-none focus:border-cyan/50 transition-colors font-medium"
          />
          <button
            onClick={phase === 'idle' ? runDemo : reset}
            disabled={phase !== 'idle' && phase !== 'result'}
            className={`absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${
              phase === 'idle' || phase === 'result'
                ? 'bg-gradient-to-r from-cyan to-cyan/80 text-void hover:shadow-lg hover:shadow-cyan/20'
                : 'bg-slate text-ash cursor-not-allowed'
            }`}
          >
            {phase === 'idle' ? (
              <><Zap className="w-4 h-4" /> Run</>
            ) : phase === 'result' ? (
              <><RotateCcw className="w-4 h-4" /> Reset</>
            ) : (
              <><Activity className="w-4 h-4 animate-pulse" /> ...</>
            )}
          </button>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 text-coral text-sm text-center"
          >
            {error}
          </motion.div>
        )}

        {/* Example prompts */}
        <div className="flex flex-wrap gap-2 mt-4 justify-center">
          {EXAMPLE_PROMPTS.map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex.text)}
              className="px-3 py-1.5 rounded-lg bg-steel/30 text-smoke text-xs hover:bg-steel/50 hover:text-white transition-all font-mono border border-transparent hover:border-slate/50"
            >
              {ex.text}
            </button>
          ))}
        </div>

        {/* Famous Attacks from Supabase */}
        <FamousAttacks
          onSelectAttack={handleSelectAttack}
          isExpanded={showFamousAttacks}
          setIsExpanded={setShowFamousAttacks}
        />
      </div>

      {/* Results */}
      <ResultsDisplay phase={phase} currentCheck={currentCheck} result={result} mode={mode} attackId={attackId} />
    </>
  )
}

// =============================================================================
// RED TEAM MODE - Hacking Challenge Interface
// =============================================================================
function RedTeamMode({ prompt, setPrompt, attackPayload, setAttackPayload, newFee, setNewFee, addFee, phase, currentCheck, result, runRedTeam, reset, error, attackId }) {
  return (
    <>
      {/* Challenge Header - Game-like framing */}
      <div className="text-center mb-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-coral/20 to-amber/10 border border-coral/40 text-coral font-bold text-sm mb-3"
        >
          <Skull className="w-5 h-5" />
          HACKER MODE ACTIVATED
          <Skull className="w-5 h-5" />
        </motion.div>
        <h3 className="text-2xl font-bold text-white mb-2">
          Try to Break Our AI Firewall
        </h3>
        <p className="text-smoke text-sm max-w-xl mx-auto">
          You are a prompt injection attacker. The user wants one thing, but you control what the AI agent actually purchases.
          <span className="text-coral font-medium"> Can you slip past VetoNet's 10 security checks?</span>
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* User Intent */}
        <div className="rounded-2xl bg-obsidian border border-slate/50 p-5">
          <h3 className="text-cyan font-medium text-sm mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            USER'S ORIGINAL INTENT
          </h3>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="What the user actually wanted..."
            className="w-full bg-steel/30 border border-slate/50 rounded-xl px-4 py-3 text-white placeholder:text-ash outline-none focus:border-cyan/50 transition-colors"
          />
          <p className="text-ash text-xs mt-3">
            VetoNet locks this intent. Your attack must try to drift from it.
          </p>
        </div>

        {/* Attack Payload */}
        <div className="rounded-2xl bg-obsidian border border-coral/20 p-5">
          <h3 className="text-coral font-medium text-sm mb-4 flex items-center gap-2">
            <Skull className="w-4 h-4" />
            YOUR ATTACK PAYLOAD
          </h3>
          <div className="space-y-3">
            <input
              type="text"
              value={attackPayload.item_description}
              onChange={(e) => setAttackPayload({ ...attackPayload, item_description: e.target.value })}
              placeholder="Item description"
              className="w-full bg-steel/30 border border-slate/50 rounded-xl px-4 py-2.5 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral/50"
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                type="number"
                value={attackPayload.unit_price}
                onChange={(e) => setAttackPayload({ ...attackPayload, unit_price: e.target.value })}
                placeholder="Price"
                className="bg-steel/30 border border-slate/50 rounded-xl px-4 py-2.5 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral/50"
              />
              <input
                type="text"
                value={attackPayload.vendor}
                onChange={(e) => setAttackPayload({ ...attackPayload, vendor: e.target.value })}
                placeholder="Vendor"
                className="bg-steel/30 border border-slate/50 rounded-xl px-4 py-2.5 text-white text-sm font-mono placeholder:text-ash outline-none focus:border-coral/50"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-smoke cursor-pointer">
              <input
                type="checkbox"
                checked={attackPayload.is_recurring}
                onChange={(e) => setAttackPayload({ ...attackPayload, is_recurring: e.target.checked })}
                className="accent-coral w-4 h-4"
              />
              Recurring charge
            </label>

            {/* Hidden Fees */}
            <div className="border-t border-slate/30 pt-3">
              <div className="text-xs text-ash mb-2">Hidden Fees:</div>
              {attackPayload.fees.map((fee, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-coral mb-1.5">
                  <span className="font-mono">{fee.name}: ${fee.amount}</span>
                  <button
                    onClick={() => setAttackPayload({
                      ...attackPayload,
                      fees: attackPayload.fees.filter((_, j) => j !== i)
                    })}
                    className="text-ash hover:text-coral transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newFee.name}
                  onChange={(e) => setNewFee({ ...newFee, name: e.target.value })}
                  placeholder="Fee name"
                  className="flex-1 bg-steel/30 border border-slate/50 rounded-lg px-3 py-1.5 text-white text-xs font-mono placeholder:text-ash outline-none"
                />
                <input
                  type="number"
                  value={newFee.amount}
                  onChange={(e) => setNewFee({ ...newFee, amount: e.target.value })}
                  placeholder="$"
                  className="w-16 bg-steel/30 border border-slate/50 rounded-lg px-3 py-1.5 text-white text-xs font-mono placeholder:text-ash outline-none"
                />
                <button
                  onClick={addFee}
                  className="px-3 py-1.5 bg-coral/20 text-coral rounded-lg text-xs font-medium hover:bg-coral/30 transition-colors"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-coral text-sm text-center mb-4"
        >
          {error}
        </motion.div>
      )}

      {/* Launch Button - Big, prominent CTA */}
      <div className="text-center mb-6">
        <motion.button
          onClick={phase === 'idle' ? runRedTeam : reset}
          disabled={phase !== 'idle' && phase !== 'result'}
          whileHover={{ scale: phase === 'idle' || phase === 'result' ? 1.03 : 1 }}
          whileTap={{ scale: phase === 'idle' || phase === 'result' ? 0.97 : 1 }}
          className={`px-10 py-4 rounded-2xl font-bold text-lg transition-all flex items-center gap-3 mx-auto ${
            phase === 'idle'
              ? 'bg-gradient-to-r from-coral via-coral to-amber text-white shadow-lg shadow-coral/30 hover:shadow-xl hover:shadow-coral/40'
              : phase === 'result'
              ? 'bg-gradient-to-r from-slate to-steel text-white hover:from-coral hover:to-coral/80'
              : 'bg-slate text-ash cursor-not-allowed'
          }`}
        >
          {phase === 'idle' ? (
            <><Swords className="w-6 h-6" /> Execute Attack</>
          ) : phase === 'result' ? (
            <><RotateCcw className="w-5 h-5" /> Try Another Attack</>
          ) : (
            <><Activity className="w-5 h-5 animate-pulse" /> Bypassing defenses...</>
          )}
        </motion.button>
        {phase === 'idle' && (
          <p className="text-ash text-xs mt-2">Press to see if your payload slips through</p>
        )}
      </div>

      {/* Results */}
      <ResultsDisplay phase={phase} currentCheck={currentCheck} result={result} isRedTeam={true} attackId={attackId} />

      {/* Victory/Defeat - Game-style feedback */}
      <AnimatePresence>
        {phase === 'result' && result && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-6 text-center"
          >
            {(result.bypassed || result.result?.approved) && detectDrift(result) ? (
              // Real bypass - payload drifted from intent but got approved
              <motion.div
                initial={{ y: 20 }}
                animate={{ y: 0 }}
                className="inline-flex flex-col items-center gap-3 px-8 py-6 rounded-2xl bg-gradient-to-br from-coral/20 to-amber/10 border-2 border-coral/50"
              >
                <motion.div
                  animate={{ rotate: [0, -10, 10, -10, 0], scale: [1, 1.1, 1] }}
                  transition={{ duration: 0.5 }}
                  className="flex items-center gap-3"
                >
                  <Trophy className="w-8 h-8 text-amber" />
                  <span className="text-coral font-black text-2xl tracking-tight">YOU WIN!</span>
                  <Trophy className="w-8 h-8 text-amber" />
                </motion.div>
                <p className="text-white text-sm font-medium">
                  You bypassed VetoNet! Your attack vector has been recorded.
                </p>
                <p className="text-ash text-xs">
                  Think you found a real vulnerability? Report it to help us improve.
                </p>
              </motion.div>
            ) : (result.bypassed || result.result?.approved) && !detectDrift(result) ? (
              // Legitimate transaction - no drift, correctly approved
              <motion.div
                initial={{ y: 20 }}
                animate={{ y: 0 }}
                className="inline-flex flex-col items-center gap-3 px-8 py-6 rounded-2xl bg-gradient-to-br from-cyan/10 to-slate/20 border-2 border-cyan/40"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-8 h-8 text-cyan" />
                  <span className="text-cyan font-black text-2xl tracking-tight">LEGITIMATE</span>
                </div>
                <p className="text-white text-sm font-medium">
                  This transaction matches the user's intent. Not an attack.
                </p>
                <p className="text-ash text-xs">
                  Try adding hidden fees, changing the price, or using a suspicious vendor.
                </p>
              </motion.div>
            ) : (
              <motion.div
                initial={{ y: 20 }}
                animate={{ y: 0 }}
                className="inline-flex flex-col items-center gap-3 px-8 py-6 rounded-2xl bg-gradient-to-br from-lime/10 to-cyan/5 border-2 border-lime/40"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-8 h-8 text-lime" />
                  <span className="text-lime font-black text-2xl tracking-tight">BLOCKED!</span>
                </div>
                <p className="text-white text-sm font-medium">
                  VetoNet caught your attack. The firewall holds strong.
                </p>
                <p className="text-ash text-xs">
                  Hint: Try hidden fees, vendor spoofing, or category drift. Get creative!
                </p>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

// =============================================================================
// RESULTS DISPLAY
// =============================================================================
function ResultsDisplay({ phase, currentCheck, result, mode, isRedTeam, attackId }) {
  if (phase === 'idle') return null

  return (
    <>
      {/* Three Column Flow */}
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        {/* Intent */}
        <motion.div
          className={`rounded-2xl border overflow-hidden ${
            phase !== 'idle' ? 'border-cyan/30 bg-cyan/5' : 'border-slate/30 bg-steel/20'
          }`}
          animate={{ opacity: phase === 'idle' ? 0.5 : 1 }}
        >
          <div className="px-4 py-2.5 border-b border-slate/30 flex items-center gap-2 bg-obsidian/50">
            <Lock className="w-3.5 h-3.5 text-cyan" />
            <span className="text-xs font-mono text-smoke">intent.lock</span>
          </div>
          <div className="p-4 min-h-[120px]">
            <div className="text-cyan text-xs font-mono mb-3 opacity-60">$ lock --intent</div>
            {result?.intent && (
              <div className="text-xs space-y-1.5 font-mono">
                <div><span className="text-ash">category:</span> <span className="text-white">{result.intent.item_category}</span></div>
                <div><span className="text-ash">max:</span> <span className="text-white">${result.intent.max_price}</span></div>
                <div><span className="text-ash">qty:</span> <span className="text-white">{result.intent.quantity}</span></div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Payload */}
        <motion.div
          className={`rounded-2xl border overflow-hidden ${
            phase === 'shopping' || phase === 'scanning' || phase === 'result'
              ? (isRedTeam || mode === 'compromised' ? 'border-coral/30 bg-coral/5' : 'border-lime/30 bg-lime/5')
              : 'border-slate/30 bg-steel/20'
          }`}
          animate={{ opacity: ['idle', 'locking'].includes(phase) ? 0.5 : 1 }}
        >
          <div className="px-4 py-2.5 border-b border-slate/30 flex items-center gap-2 bg-obsidian/50">
            <Bot className="w-3.5 h-3.5 text-smoke" />
            <span className="text-xs font-mono text-smoke">agent_payload</span>
          </div>
          <div className="p-4 min-h-[120px]">
            {result?.payload && (
              <div className="text-xs space-y-1.5 font-mono">
                <div className="text-white truncate">{result.payload.item_description}</div>
                <div><span className="text-ash">vendor:</span> <span className="text-white">{result.payload.vendor}</span></div>
                <div><span className="text-ash">price:</span> <span className="text-white">${result.payload.unit_price}</span></div>
                {result.payload.fees?.length > 0 && (
                  <div className="text-coral">+fees: ${result.payload.fees.reduce((a, f) => a + f.amount, 0)}</div>
                )}
              </div>
            )}
          </div>
        </motion.div>

        {/* Decision */}
        <motion.div
          className={`rounded-2xl border overflow-hidden ${
            phase === 'result'
              ? (result?.result?.approved ? 'border-lime/30 bg-lime/5' : 'border-coral/30 bg-coral/5')
              : 'border-slate/30 bg-steel/20'
          }`}
          animate={{ opacity: ['idle', 'locking', 'shopping'].includes(phase) ? 0.5 : 1 }}
        >
          <div className="px-4 py-2.5 border-b border-slate/30 flex items-center gap-2 bg-obsidian/50">
            <Shield className="w-3.5 h-3.5 text-smoke" />
            <span className="text-xs font-mono text-smoke">vetonet</span>
          </div>
          <div className="p-4 min-h-[120px] flex items-center justify-center">
            {phase === 'result' && result && (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-center"
              >
                {result.result?.approved ? (
                  <>
                    <ShieldCheck className="w-12 h-12 mx-auto text-lime mb-2" strokeWidth={1.5} />
                    <div className="text-lime font-bold text-lg">APPROVED</div>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-12 h-12 mx-auto text-coral mb-2" strokeWidth={1.5} />
                    <div className="text-coral font-bold text-lg">VETOED</div>
                  </>
                )}
              </motion.div>
            )}
            {phase === 'scanning' && (
              <div className="text-cyan text-sm font-mono flex items-center gap-2">
                <Activity className="w-4 h-4 animate-pulse" />
                Scanning...
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Security Checks Grid */}
      {(phase === 'scanning' || phase === 'result') && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
            {(result?.result?.checks || SECURITY_CHECKS).map((check, i) => {
              const isActive = i <= currentCheck
              const passed = check.passed !== false
              const failed = isActive && !passed

              return (
                <motion.div
                  key={check.id || i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: isActive ? 1 : 0.4, scale: 1 }}
                  transition={{ delay: i * 0.05 }}
                  className={`rounded-xl p-3 text-center border transition-all ${
                    failed ? 'bg-coral/10 border-coral/40' :
                    isActive ? 'bg-cyan/10 border-cyan/30' :
                    'bg-steel/20 border-slate/30'
                  }`}
                >
                  {failed ? (
                    <XCircle className="w-5 h-5 mx-auto text-coral" />
                  ) : isActive ? (
                    <CheckCircle2 className="w-5 h-5 mx-auto text-cyan" />
                  ) : (
                    <div className="w-5 h-5 mx-auto rounded-full border-2 border-slate/50" />
                  )}
                  <div className={`font-mono text-[10px] mt-1.5 truncate w-full px-0.5 ${
                    failed ? 'text-coral' : isActive ? 'text-white' : 'text-ash'
                  }`} title={check.name}>
                    {check.name.replace(/_/g, ' ')}
                  </div>
                </motion.div>
              )
            })}
          </div>

          {/* Violations */}
          {phase === 'result' && result?.result?.checks?.some(c => !c.passed) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 rounded-2xl bg-coral/5 border border-coral/30 p-4 max-w-2xl mx-auto"
            >
              <h4 className="text-coral font-medium text-sm mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                VIOLATIONS DETECTED
              </h4>
              <div className="space-y-2">
                {result.result.checks.filter(c => !c.passed).map((c, i) => (
                  <div key={i} className="text-sm flex items-start gap-2">
                    <XCircle className="w-4 h-4 text-coral mt-0.5 flex-shrink-0" />
                    <span className="text-white font-medium">{c.name}:</span>
                    <span className="text-smoke">{c.reason}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Feedback Buttons */}
          {phase === 'result' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-6 flex justify-center"
            >
              <FeedbackButtons attackId={attackId} />
            </motion.div>
          )}
        </motion.div>
      )}
    </>
  )
}

// =============================================================================
// FOOTER
// =============================================================================
function Footer() {
  return (
    <footer className="relative z-10 border-t border-slate/30 py-8 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-cyan" />
          <span className="text-white font-medium">VetoNet</span>
          <span className="text-ash text-sm">Semantic Firewall for AI Agents</span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <a
            href="https://github.com/takenosuke-code/vetonet"
            target="_blank"
            rel="noopener noreferrer"
            className="text-smoke hover:text-white transition-colors flex items-center gap-1.5"
          >
            GitHub <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <a
            href="https://pypi.org/project/vetonet/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-smoke hover:text-white transition-colors flex items-center gap-1.5"
          >
            PyPI <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </footer>
  )
}

// =============================================================================
// MAIN APP
// =============================================================================
function App() {
  const [stats, setStats] = useState({
    total_attempts: 0,
    blocked: 0,
    bypassed: 0,
    bypass_rate: 0
  })
  const [challengeMode, setChallengeMode] = useState(null)
  const playgroundRef = useRef(null)

  const handleAcceptChallenge = () => {
    setChallengeMode('redteam')
    // Scroll to playground
    setTimeout(() => {
      playgroundRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      // Try Railway API first (until Supabase key is configured in Vercel env vars)
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) {
        const data = await res.json()
        // Railway has 1000, but we can override with Supabase count if available
        try {
          const [totalRes, blockedRes, bypassedRes] = await Promise.all([
            supabase.from('attacks').select('*', { count: 'exact', head: true }),
            supabase.from('attacks').select('*', { count: 'exact', head: true }).eq('verdict', 'blocked'),
            supabase.from('attacks').select('*', { count: 'exact', head: true }).eq('verdict', 'approved')
          ])
          if (totalRes.count && totalRes.count > 0) {
            setStats({
              total_attempts: totalRes.count,
              blocked: blockedRes.count || 0,
              bypassed: bypassedRes.count || 0,
              bypass_rate: totalRes.count > 0 ? ((bypassedRes.count / totalRes.count) * 100).toFixed(1) : 0,
              feedback_count: 0
            })
            return
          }
        } catch {
          // Supabase failed, use Railway data
        }
        setStats(data)
      }
    } catch (e) {
      // Both failed, try Supabase directly
      try {
        const [totalRes, blockedRes, bypassedRes] = await Promise.all([
          supabase.from('attacks').select('*', { count: 'exact', head: true }),
          supabase.from('attacks').select('*', { count: 'exact', head: true }).eq('verdict', 'blocked'),
          supabase.from('attacks').select('*', { count: 'exact', head: true }).eq('verdict', 'approved')
        ])
        setStats({
          total_attempts: totalRes.count || 0,
          blocked: blockedRes.count || 0,
          bypassed: bypassedRes.count || 0,
          bypass_rate: totalRes.count > 0 ? ((bypassedRes.count / totalRes.count) * 100).toFixed(1) : 0,
          feedback_count: 0
        })
      } catch {
        // Both failed
      }
    }
  }

  return (
    <div className="min-h-screen bg-void grid-bg relative noise">
      <HeroSection stats={stats} />
      <HowItWorks />
      <BeforeAfterComparison />
      <ChallengeBanner stats={stats} onAcceptChallenge={handleAcceptChallenge} />
      <Playground stats={stats} fetchStats={fetchStats} playgroundRef={playgroundRef} initialMode={challengeMode} />
      <AttackLeaderboard />
      <LiveFeed />
      <Footer />
    </div>
  )
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export default App
