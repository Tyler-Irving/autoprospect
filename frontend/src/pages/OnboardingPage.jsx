import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAgentStore } from '../store/agentStore'

const TOTAL_STEPS = 5

const COMMON_INDUSTRIES = [
  'Plumber', 'HVAC Contractor', 'Electrician', 'Roofer', 'Landscaper',
  'Painter', 'Pest Control', 'Cleaning Service', 'Garage Door', 'Flooring',
  'Dentist', 'Chiropractor', 'Physical Therapist', 'Optometrist', 'Veterinarian',
  'Auto Repair', 'Restaurant', 'Beauty Salon', 'Gym / Fitness', 'Retail',
]

const TONE_OPTIONS = [
  { value: 'formal', label: 'Formal & Professional', desc: 'Polished, no contractions, business-appropriate.' },
  { value: 'semi_formal', label: 'Friendly & Professional', desc: 'Warm but credible — the sweet spot for most B2B.' },
  { value: 'casual', label: 'Casual & Conversational', desc: 'First-name basis, natural, feels human.' },
]

function StepIndicator({ current }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
        <div
          key={i}
          className="h-1 rounded-full flex-1 transition-all duration-300"
          style={{ background: i < current ? '#f97316' : 'var(--border)' }}
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 1: Welcome
// ---------------------------------------------------------------------------
function StepWelcome({ onNext }) {
  return (
    <div className="flex flex-col items-center text-center gap-6">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-extrabold text-xl"
        style={{ background: '#f97316' }}
      >
        AP
      </div>
      <div>
        <h1 className="text-2xl font-semibold mb-2" style={{ color: 'var(--foreground)' }}>
          Welcome to AutoProspect
        </h1>
        <p className="text-sm max-w-sm" style={{ color: 'var(--muted-foreground)' }}>
          Let's take 2 minutes to set up your AI prospecting agent. It will learn
          what you sell, who you sell to, and how you like to communicate — then
          find and score leads automatically.
        </p>
      </div>
      <button
        onClick={onNext}
        className="px-8 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-90"
        style={{ background: '#f97316', color: '#fff' }}
      >
        Get started →
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2: Your Service
// ---------------------------------------------------------------------------
function StepService({ values, onChange, onNext, onBack, saving }) {
  const valid = values.service_name.trim().length > 0

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--foreground)' }}>
          What do you sell?
        </h2>
        <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          Give your agent a clear picture of your product or service.
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Service name <span style={{ color: '#f97316' }}>*</span>
        </label>
        <input
          type="text"
          placeholder="e.g. CRM automation for dental offices"
          value={values.service_name}
          onChange={(e) => onChange('service_name', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm outline-none"
          style={{
            background: 'var(--muted)',
            border: '1px solid var(--border)',
            color: 'var(--foreground)',
          }}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Brief description
        </label>
        <textarea
          rows={3}
          placeholder="We build scheduling and invoicing tools that replace spreadsheets and sticky notes..."
          value={values.service_description}
          onChange={(e) => onChange('service_description', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
          style={{
            background: 'var(--muted)',
            border: '1px solid var(--border)',
            color: 'var(--foreground)',
          }}
        />
      </div>

      <NavButtons onBack={onBack} onNext={onNext} nextDisabled={!valid || saving} saving={saving} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 3: Your Customers
// ---------------------------------------------------------------------------
function StepCustomers({ values, onChange, onNext, onBack, saving }) {
  const toggle = (industry) => {
    const current = values.target_industries
    const next = current.includes(industry)
      ? current.filter((i) => i !== industry)
      : [...current, industry]
    onChange('target_industries', next)
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--foreground)' }}>
          Who are your ideal customers?
        </h2>
        <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          Select the industries you target. Your agent will prioritize these.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {COMMON_INDUSTRIES.map((ind) => {
          const selected = values.target_industries.includes(ind)
          return (
            <button
              key={ind}
              onClick={() => toggle(ind)}
              className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
              style={{
                background: selected ? '#f97316' : 'var(--muted)',
                color: selected ? '#fff' : 'var(--muted-foreground)',
                border: `1px solid ${selected ? '#f97316' : 'var(--border)'}`,
              }}
            >
              {ind}
            </button>
          )
        })}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Describe your ideal customer (optional)
        </label>
        <textarea
          rows={2}
          placeholder="Small home service businesses with 1-10 employees, no current software..."
          value={values.target_biz_description}
          onChange={(e) => onChange('target_biz_description', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
          style={{
            background: 'var(--muted)',
            border: '1px solid var(--border)',
            color: 'var(--foreground)',
          }}
        />
      </div>

      <NavButtons onBack={onBack} onNext={onNext} saving={saving} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 4: Outreach Style
// ---------------------------------------------------------------------------
function StepOutreach({ values, onChange, onNext, onBack, saving }) {
  const setPoint = (i, val) => {
    const pts = [...values.key_selling_points]
    pts[i] = val
    onChange('key_selling_points', pts)
  }

  const addPoint = () => {
    if (values.key_selling_points.length < 5)
      onChange('key_selling_points', [...values.key_selling_points, ''])
  }

  const removePoint = (i) => {
    onChange('key_selling_points', values.key_selling_points.filter((_, idx) => idx !== i))
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--foreground)' }}>
          How does your agent communicate?
        </h2>
        <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          This shapes every cold email and call script your agent generates.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Tone
        </label>
        {TONE_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className="flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors"
            style={{
              background: values.outreach_tone === opt.value ? 'rgba(249,115,22,0.08)' : 'var(--muted)',
              border: `1px solid ${values.outreach_tone === opt.value ? '#f97316' : 'var(--border)'}`,
            }}
          >
            <input
              type="radio"
              name="tone"
              value={opt.value}
              checked={values.outreach_tone === opt.value}
              onChange={() => onChange('outreach_tone', opt.value)}
              className="mt-0.5"
              style={{ accentColor: '#f97316' }}
            />
            <div>
              <div className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>{opt.label}</div>
              <div className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{opt.desc}</div>
            </div>
          </label>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Key selling points (up to 5)
        </label>
        {values.key_selling_points.map((pt, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="text"
              placeholder={`e.g. No long-term contracts`}
              value={pt}
              onChange={(e) => setPoint(i, e.target.value)}
              className="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
              style={{
                background: 'var(--muted)',
                border: '1px solid var(--border)',
                color: 'var(--foreground)',
              }}
            />
            <button
              onClick={() => removePoint(i)}
              className="text-xs px-2 py-1 rounded"
              style={{ color: 'var(--muted-foreground)' }}
            >
              ✕
            </button>
          </div>
        ))}
        {values.key_selling_points.length < 5 && (
          <button
            onClick={addPoint}
            className="text-xs self-start px-3 py-1.5 rounded-lg transition-colors"
            style={{ color: '#f97316', border: '1px dashed #f97316' }}
          >
            + Add point
          </button>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium" style={{ color: 'var(--muted-foreground)' }}>
          Anything else Claude should know? (optional)
        </label>
        <textarea
          rows={2}
          placeholder="We specialize in family-owned businesses. Avoid mentioning competitors..."
          value={values.custom_talking_points}
          onChange={(e) => onChange('custom_talking_points', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
          style={{
            background: 'var(--muted)',
            border: '1px solid var(--border)',
            color: 'var(--foreground)',
          }}
        />
      </div>

      <NavButtons onBack={onBack} onNext={onNext} saving={saving} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 5: Review & Launch
// ---------------------------------------------------------------------------
function StepReview({ values, onBack, onLaunch, saving }) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--foreground)' }}>
          Your agent is ready
        </h2>
        <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          Review your setup. You can change any of this later from the Agent page.
        </p>
      </div>

      <div
        className="rounded-xl p-4 flex flex-col gap-3 text-sm"
        style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}
      >
        <ReviewRow label="Service" value={values.service_name || '—'} />
        {values.service_description && (
          <ReviewRow label="Description" value={values.service_description} />
        )}
        <ReviewRow
          label="Target industries"
          value={values.target_industries.length ? values.target_industries.join(', ') : '—'}
        />
        <ReviewRow label="Tone" value={TONE_OPTIONS.find(t => t.value === values.outreach_tone)?.label || '—'} />
        {values.key_selling_points.filter(Boolean).length > 0 && (
          <ReviewRow label="Selling points" value={values.key_selling_points.filter(Boolean).join(', ')} />
        )}
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-70"
          style={{ border: '1px solid var(--border)', color: 'var(--muted-foreground)' }}
        >
          Back
        </button>
        <button
          onClick={onLaunch}
          disabled={saving}
          className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          style={{ background: '#f97316', color: '#fff' }}
        >
          {saving ? 'Launching…' : 'Launch my agent →'}
        </button>
      </div>
    </div>
  )
}

function ReviewRow({ label, value }) {
  return (
    <div className="flex gap-3">
      <span className="w-32 shrink-0 text-xs" style={{ color: 'var(--muted-foreground)' }}>{label}</span>
      <span style={{ color: 'var(--foreground)' }}>{value}</span>
    </div>
  )
}

function NavButtons({ onBack, onNext, nextDisabled = false, saving = false }) {
  return (
    <div className="flex gap-3 pt-2">
      {onBack && (
        <button
          onClick={onBack}
          className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-70"
          style={{ border: '1px solid var(--border)', color: 'var(--muted-foreground)' }}
        >
          Back
        </button>
      )}
      <button
        onClick={onNext}
        disabled={nextDisabled || saving}
        className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
        style={{ background: '#f97316', color: '#fff' }}
      >
        {saving ? 'Saving…' : 'Next →'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main wizard
// ---------------------------------------------------------------------------
export default function OnboardingPage() {
  const navigate = useNavigate()
  const { config, updateConfig, completeOnboarding } = useAgentStore()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [values, setValues] = useState({
    service_name: config?.service_name || '',
    service_description: config?.service_description || '',
    target_industries: config?.target_industries || [],
    target_biz_description: config?.target_biz_description || '',
    outreach_tone: config?.outreach_tone || 'semi_formal',
    key_selling_points: config?.key_selling_points?.length ? config.key_selling_points : [],
    custom_talking_points: config?.custom_talking_points || '',
  })

  const onChange = (field, val) => setValues((v) => ({ ...v, [field]: val }))

  const saveAndNext = async (fields) => {
    setSaving(true)
    try {
      await updateConfig(fields)
      setStep((s) => s + 1)
    } finally {
      setSaving(false)
    }
  }

  const handleLaunch = async () => {
    setSaving(true)
    try {
      await updateConfig({
        key_selling_points: values.key_selling_points.filter(Boolean),
        custom_talking_points: values.custom_talking_points,
      })
      await completeOnboarding()
      navigate('/', { replace: true })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'var(--background)' }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-8"
        style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
      >
        {step > 1 && <StepIndicator current={step - 1} />}

        {step === 1 && <StepWelcome onNext={() => setStep(2)} />}

        {step === 2 && (
          <StepService
            values={values}
            onChange={onChange}
            onBack={() => setStep(1)}
            onNext={() =>
              saveAndNext({
                service_name: values.service_name,
                service_description: values.service_description,
              })
            }
            saving={saving}
          />
        )}

        {step === 3 && (
          <StepCustomers
            values={values}
            onChange={onChange}
            onBack={() => setStep(2)}
            onNext={() =>
              saveAndNext({
                target_industries: values.target_industries,
                target_biz_description: values.target_biz_description,
              })
            }
            saving={saving}
          />
        )}

        {step === 4 && (
          <StepOutreach
            values={values}
            onChange={onChange}
            onBack={() => setStep(3)}
            onNext={() =>
              saveAndNext({
                outreach_tone: values.outreach_tone,
                key_selling_points: values.key_selling_points.filter(Boolean),
                custom_talking_points: values.custom_talking_points,
              })
            }
            saving={saving}
          />
        )}

        {step === 5 && (
          <StepReview
            values={values}
            onBack={() => setStep(4)}
            onLaunch={handleLaunch}
            saving={saving}
          />
        )}
      </div>
    </div>
  )
}
