import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Swords, Trophy, Target, ArrowLeft } from 'lucide-react'
import {
  ChallengeBanner,
  Playground,
  AttackLeaderboard,
  LiveFeed,
  API_BASE
} from './App'
import './index.css'

// =============================================================================
// CHALLENGE PAGE - Red Team / Playground
// =============================================================================
export default function ChallengePage() {
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
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats({
          total_attempts: data.total_attempts || 0,
          blocked: data.blocked || 0,
          bypassed: data.bypassed || 0,
          bypass_rate: data.bypass_rate || 0,
          feedback_count: data.feedback_count || 0
        })
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  return (
    <div className="min-h-screen bg-void">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,71,87,0.05)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(255,184,48,0.03)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,71,87,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(255,71,87,0.01)_1px,transparent_1px)] bg-[size:60px_60px]" />
      </div>

      {/* Nav */}
      <nav className="relative z-20 px-6 py-4 border-b border-slate/30 bg-void/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 text-smoke hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            <Shield className="w-6 h-6 text-cyan" />
            <span className="font-semibold text-white">VetoNet</span>
          </Link>
          <div className="flex items-center gap-2">
            <Swords className="w-5 h-5 text-coral" />
            <span className="text-white font-medium">Red Team Challenge</span>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <header className="relative z-10 py-12 px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-3xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-coral/10 border border-coral/20 text-coral text-sm font-mono mb-6">
            <Target className="w-4 h-4" />
            OPEN CHALLENGE
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Can You <span className="text-coral">Bypass</span> VetoNet?
          </h1>
          <p className="text-smoke text-lg max-w-xl mx-auto">
            Craft malicious payloads. Try to trick the semantic firewall.
            Only <span className="text-coral font-bold">{stats.bypass_rate}%</span> of attacks succeed.
          </p>
        </motion.div>
      </header>

      {/* Stats Bar */}
      <div className="relative z-10 px-6 pb-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-obsidian border border-slate/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-white">{stats.total_attempts.toLocaleString()}</div>
              <div className="text-xs text-ash">Attacks Tested</div>
            </div>
            <div className="bg-obsidian border border-lime/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-lime">{stats.blocked.toLocaleString()}</div>
              <div className="text-xs text-ash">Blocked</div>
            </div>
            <div className="bg-obsidian border border-coral/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-coral">{stats.bypassed}</div>
              <div className="text-xs text-ash">Bypassed</div>
            </div>
            <div className="bg-obsidian border border-amber/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-amber">{(100 - stats.bypass_rate).toFixed(1)}%</div>
              <div className="text-xs text-ash">Block Rate</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="relative z-10 px-6 pb-12">
        <div className="max-w-5xl mx-auto space-y-8">
          {/* Playground */}
          <div ref={playgroundRef}>
            <Playground
              stats={stats}
              fetchStats={fetchStats}
              playgroundRef={playgroundRef}
              initialMode={challengeMode || 'redteam'}
            />
          </div>

          {/* Leaderboard */}
          <AttackLeaderboard />

          {/* Live Feed */}
          <LiveFeed />
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate/30 py-6 px-6">
        <div className="max-w-5xl mx-auto flex items-center justify-between text-sm">
          <Link to="/" className="text-smoke hover:text-white transition-colors">
            Back to VetoNet
          </Link>
          <div className="flex items-center gap-2 text-ash">
            <Trophy className="w-4 h-4 text-amber" />
            Find a bypass? Your attack joins the leaderboard.
          </div>
        </div>
      </footer>
    </div>
  )
}
