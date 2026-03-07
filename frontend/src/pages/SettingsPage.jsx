import { useEffect, useState } from 'react'
import { useToasts } from '@/components/ui/toast'
import { settingsApi } from '../api/settings'

function KeyRow({ label, masked, isSet }) {
  return (
    <div className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-sm" style={{ color: 'var(--muted-foreground)' }}>{label}</span>
      <div className="flex items-center gap-2">
        {isSet ? (
          <>
            <span className="text-sm font-mono tracking-wider" style={{ color: 'var(--foreground)' }}>{masked}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, #22c55e 15%, transparent)', color: '#22c55e', border: '1px solid color-mix(in srgb, #22c55e 30%, transparent)' }}>
              configured
            </span>
          </>
        ) : (
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, #ef4444 15%, transparent)', color: '#ef4444', border: '1px solid color-mix(in srgb, #ef4444 30%, transparent)' }}>
            not set
          </span>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="rounded-xl p-5 space-y-1" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <h2 className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--muted-foreground)' }}>{title}</h2>
      {children}
    </div>
  )
}

export default function SettingsPage() {
  const toasts = useToasts()
  const [config, setConfig] = useState(null)
  const [budget, setBudget] = useState('')
  const [maxBusinesses, setMaxBusinesses] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    settingsApi.get()
      .then(({ data }) => {
        setConfig(data)
        setBudget(String(Math.round(data.monthly_budget_cents / 100)))
        setMaxBusinesses(String(data.max_businesses_per_scan))
      })
      .catch(() => toasts.error('Failed to load settings'))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const budgetCents = Math.round(parseFloat(budget) * 100)
      const max = parseInt(maxBusinesses, 10)
      if (isNaN(budgetCents) || budgetCents < 0) {
        toasts.error('Invalid budget amount')
        return
      }
      if (isNaN(max) || max < 1) {
        toasts.error('Max businesses must be at least 1')
        return
      }
      const { data } = await settingsApi.patch({
        monthly_budget_cents: budgetCents,
        max_businesses_per_scan: max,
      })
      setConfig(data)
      toasts.success('Settings saved')
    } catch {
      toasts.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (!config) {
    return (
      <div className="h-full flex items-center justify-center text-sm" style={{ background: 'var(--background)', color: 'var(--muted-foreground)' }}>
        Loading…
      </div>
    )
  }

  const monthlyBudgetDollars = config.monthly_budget_cents / 100

  return (
    <div className="h-full overflow-auto p-6" style={{ background: 'var(--background)' }}>
      <div className="max-w-2xl mx-auto space-y-6">

        <h1 className="text-lg font-semibold" style={{ color: 'var(--foreground)' }}>Settings</h1>

        {/* Budget + scan limits */}
        <Section title="Scan Limits">
          <div className="space-y-4 pt-1">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
                Monthly AI Budget (USD)
              </label>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--muted-foreground)' }}>$</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="w-32 px-3 py-2 rounded-lg text-sm focus:outline-none"
                  style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
                />
                <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                  / month — current budget: <span style={{ color: 'var(--foreground)' }}>${monthlyBudgetDollars.toFixed(0)}</span>
                </span>
              </div>
              <p className="text-xs mt-1.5" style={{ color: 'var(--muted-foreground)' }}>
                Claude API spend target. Scans will not be blocked when over budget — this is informational only.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
                Max Businesses per Scan
              </label>
              <input
                type="number"
                min="1"
                max="1000"
                value={maxBusinesses}
                onChange={(e) => setMaxBusinesses(e.target.value)}
                className="w-32 px-3 py-2 rounded-lg text-sm focus:outline-none"
                style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
              />
              <p className="text-xs mt-1.5" style={{ color: 'var(--muted-foreground)' }}>
                Limits how many businesses are discovered and enriched per scan.
              </p>
            </div>

            <div className="flex justify-end pt-1">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </Section>

        {/* API Keys */}
        <Section title="API Keys">
          <p className="text-xs pb-2" style={{ color: 'var(--muted-foreground)' }}>
            Configured via <code className="px-1 rounded text-xs" style={{ background: 'var(--secondary)' }}>.env</code>. Keys are masked for security.
          </p>
          <KeyRow label="Google Places API Key" masked={config.google_places_key_masked} isSet={config.google_places_key_set} />
          <KeyRow label="Anthropic API Key" masked={config.anthropic_key_masked} isSet={config.anthropic_key_set} />
          <KeyRow label="Resend API Key" masked={config.resend_key_masked} isSet={config.resend_key_set} />
        </Section>

        {/* Email config */}
        <Section title="Email">
          <p className="text-xs pb-2" style={{ color: 'var(--muted-foreground)' }}>
            Configured via <code className="px-1 rounded text-xs" style={{ background: 'var(--secondary)' }}>.env</code>. Edit the file to change these values.
          </p>
          <div className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <span className="text-sm" style={{ color: 'var(--muted-foreground)' }}>From address</span>
            <span className="text-sm font-mono" style={{ color: config.email_from ? 'var(--foreground)' : 'var(--muted-foreground)' }}>
              {config.email_from || 'not set'}
            </span>
          </div>
          <div className="flex items-center justify-between py-2.5">
            <span className="text-sm" style={{ color: 'var(--muted-foreground)' }}>Reply-to address</span>
            <span className="text-sm font-mono" style={{ color: config.email_reply_to ? 'var(--foreground)' : 'var(--muted-foreground)' }}>
              {config.email_reply_to || 'not set'}
            </span>
          </div>
        </Section>

      </div>
    </div>
  )
}
