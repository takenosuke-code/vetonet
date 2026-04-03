import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createClient } from '@supabase/supabase-js'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Key, Copy, Check, LogOut, Plus, Trash2, ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { API_BASE, LINKS } from './config'
import './index.css'

// Supabase client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null

export default function AuthPage() {
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authMode, setAuthMode] = useState('signin') // signin, signup
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  // API Keys state
  const [keys, setKeys] = useState([])
  const [newKey, setNewKey] = useState(null)
  const [copied, setCopied] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [creatingKey, setCreatingKey] = useState(false)

  useEffect(() => {
    if (!supabase) {
      setLoading(false)
      setError('Supabase not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to .env')
      return
    }

    // Check existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) fetchKeys(session)
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      if (session) fetchKeys(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const fetchKeys = async (session) => {
    if (!session) return
    try {
      const res = await fetch(`${API_BASE}/keys`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      if (res.ok) {
        // Verify response is JSON before parsing
        const contentType = res.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          const data = await res.json()
          setKeys(data.keys || [])
        } else {
          console.error('API returned non-JSON response')
        }
      }
    } catch (e) {
      console.error('Failed to fetch keys:', e)
    }
  }

  const handleAuth = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)

    try {
      if (authMode === 'signup') {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        })
        if (error) throw error
        setMessage('Check your email for the confirmation link!')
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
      }
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setSession(null)
    setKeys([])
  }

  const createApiKey = async () => {
    if (!session) return
    setCreatingKey(true)
    setError('')

    try {
      const res = await fetch(`${API_BASE}/keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          name: keyName || 'My API Key',
          environment: 'live'
        })
      })

      // Check content type before parsing as JSON
      const contentType = res.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('API returned non-JSON response. The server may be unavailable.')
      }

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to create key')

      setNewKey(data.key)
      setKeyName('')
      fetchKeys(session)
    } catch (err) {
      setError(err.message)
    }
    setCreatingKey(false)
  }

  const deleteKey = async (keyId) => {
    if (!session || !confirm('Are you sure? This will immediately revoke the key.')) return

    try {
      const res = await fetch(`${API_BASE}/keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      if (res.ok) {
        fetchKeys(session)
      }
    } catch (e) {
      console.error('Failed to delete key:', e)
    }
  }

  const copyKey = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <div className="text-smoke">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-void">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(0,255,209,0.05)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,209,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,209,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />
      </div>

      {/* Nav */}
      <nav className="relative z-20 px-6 py-4 border-b border-slate/30 bg-void/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 text-smoke hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            <Shield className="w-6 h-6 text-cyan" />
            <span className="font-semibold text-white">VetoNet</span>
          </Link>
          {session && (
            <button
              onClick={handleSignOut}
              className="flex items-center gap-2 text-smoke hover:text-white text-sm transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          )}
        </div>
      </nav>

      <main className="relative z-10 px-6 py-12">
        <div className="max-w-xl mx-auto">
          {!session ? (
            // Auth Form
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-obsidian border border-slate/30 rounded-2xl p-8"
            >
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-cyan/10 border border-cyan/20 mb-4">
                  <Key className="w-8 h-8 text-cyan" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">
                  {authMode === 'signup' ? 'Create Account' : 'Sign In'}
                </h1>
                <p className="text-smoke">
                  {authMode === 'signup'
                    ? 'Create an account to get your API key'
                    : 'Sign in to manage your API keys'}
                </p>
              </div>

              <form onSubmit={handleAuth} className="space-y-4">
                <div>
                  <label className="block text-sm text-smoke mb-2">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-steel/30 border border-slate/50 rounded-xl px-4 py-3 text-white placeholder:text-ash outline-none focus:border-cyan/50 transition-colors"
                    placeholder="you@example.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm text-smoke mb-2">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-steel/30 border border-slate/50 rounded-xl px-4 py-3 text-white placeholder:text-ash outline-none focus:border-cyan/50 transition-colors pr-12"
                      placeholder="Enter password"
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-ash hover:text-white transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="text-coral text-sm bg-coral/10 border border-coral/20 rounded-lg px-4 py-2">
                    {error}
                  </div>
                )}

                {message && (
                  <div className="text-lime text-sm bg-lime/10 border border-lime/20 rounded-lg px-4 py-2">
                    {message}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-cyan text-void font-semibold rounded-xl hover:bg-cyan/90 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Loading...' : authMode === 'signup' ? 'Create Account' : 'Sign In'}
                </button>
              </form>

              <div className="mt-6 text-center text-sm text-smoke">
                {authMode === 'signup' ? (
                  <>
                    Already have an account?{' '}
                    <button onClick={() => setAuthMode('signin')} className="text-cyan hover:underline">
                      Sign in
                    </button>
                  </>
                ) : (
                  <>
                    Don't have an account?{' '}
                    <button onClick={() => setAuthMode('signup')} className="text-cyan hover:underline">
                      Create one
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          ) : (
            // Dashboard - API Keys
            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-8"
              >
                <h1 className="text-2xl font-bold text-white mb-2">API Keys</h1>
                <p className="text-smoke">Manage your VetoNet API keys</p>
              </motion.div>

              {/* New Key Display */}
              <AnimatePresence>
                {newKey && (
                  <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="bg-lime/10 border-2 border-lime/30 rounded-2xl p-6"
                  >
                    <div className="flex items-center gap-2 text-lime mb-3">
                      <Check className="w-5 h-5" />
                      <span className="font-semibold">Key Created - Save it now!</span>
                    </div>
                    <div className="flex items-center gap-3 bg-obsidian rounded-xl p-4">
                      <code className="flex-1 text-white font-mono text-sm break-all">
                        {newKey}
                      </code>
                      <button
                        onClick={copyKey}
                        className="p-2 bg-slate/30 rounded-lg hover:bg-slate/50 transition-colors text-white"
                      >
                        {copied ? <Check className="w-4 h-4 text-lime" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-amber text-xs mt-3">
                      This key will not be shown again. Store it securely.
                    </p>
                    <button
                      onClick={() => setNewKey(null)}
                      className="mt-4 text-smoke hover:text-white text-sm transition-colors"
                    >
                      Dismiss
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Create Key */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-obsidian border border-slate/30 rounded-2xl p-6"
              >
                <h2 className="text-lg font-semibold text-white mb-4">Create New Key</h2>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="Key name (optional)"
                    className="flex-1 bg-steel/30 border border-slate/50 rounded-xl px-4 py-3 text-white placeholder:text-ash outline-none focus:border-cyan/50 transition-colors"
                  />
                  <button
                    onClick={createApiKey}
                    disabled={creatingKey}
                    className="px-6 py-3 bg-cyan text-void font-semibold rounded-xl hover:bg-cyan/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Create
                  </button>
                </div>
                {error && (
                  <p className="text-coral text-sm mt-3">{error}</p>
                )}
              </motion.div>

              {/* Existing Keys */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-obsidian border border-slate/30 rounded-2xl overflow-hidden"
              >
                <div className="px-6 py-4 border-b border-slate/30">
                  <h2 className="text-lg font-semibold text-white">Your Keys</h2>
                </div>
                {keys.length === 0 ? (
                  <div className="p-8 text-center text-ash">
                    No API keys yet. Create one above.
                  </div>
                ) : (
                  <div className="divide-y divide-slate/20">
                    {keys.map((key) => (
                      <div key={key.id} className="px-6 py-4 flex items-center justify-between">
                        <div>
                          <div className="font-mono text-white">
                            {key.key_prefix}...
                          </div>
                          <div className="text-xs text-ash mt-1">
                            {key.name || 'Unnamed'} · Created {new Date(key.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        <button
                          onClick={() => deleteKey(key.id)}
                          className="p-2 text-ash hover:text-coral transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
