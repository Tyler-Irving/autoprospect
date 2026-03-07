import { useState, useEffect } from 'react'
import { useAgentStore } from '../store/agentStore'
import toast from 'react-hot-toast'

// ── Schedule constants ─────────────────────────────────────────────────────────
const CRON_PRESETS = [
  { label: 'Daily at 9am', value: '0 9 * * *' },
  { label: 'Weekdays at 9am', value: '0 9 * * 1-5' },
  { label: 'Mon / Wed / Fri', value: '0 9 * * 1,3,5' },
  { label: 'Weekly (Monday)', value: '0 9 * * 1' },
]

const PLACE_TYPE_OPTIONS = [
  { value: 'plumber', label: 'Plumber' },
  { value: 'hvac_contractor', label: 'HVAC' },
  { value: 'electrician', label: 'Electrician' },
  { value: 'landscaper', label: 'Landscaper' },
  { value: 'lawn_care_service', label: 'Lawn Care' },
  { value: 'cleaning_service', label: 'Cleaning' },
  { value: 'pest_control', label: 'Pest Control' },
  { value: 'roofing_contractor', label: 'Roofer' },
  { value: 'painter', label: 'Painter' },
  { value: 'general_contractor', label: 'Contractor' },
  { value: 'auto_repair', label: 'Auto Repair' },
  { value: 'dentist', label: 'Dentist' },
  { value: 'chiropractor', label: 'Chiropractor' },
  { value: 'veterinary_care', label: 'Vet' },
  { value: 'beauty_salon', label: 'Salon' },
  { value: 'gym', label: 'Gym' },
  { value: 'restaurant', label: 'Restaurant' },
]

const EMPTY_SCHEDULE_FORM = {
  name: '',
  cron_expression: '0 9 * * 1-5',
  scan_place_types: [],
  scan_keyword: '',
  scan_radius_meters: 5000,
  is_active: true,
}

const TONE_OPTIONS = [
  { value: 'formal', label: 'Formal', desc: 'Professional, polished — best for corporate or medical clients.' },
  { value: 'semi_formal', label: 'Semi-formal', desc: 'Friendly but professional — works for most industries.' },
  { value: 'casual', label: 'Casual', desc: 'Conversational, direct — great for small trades businesses.' },
]

const COMMON_INDUSTRIES = [
  { value: 'plumber', label: 'Plumber' },
  { value: 'hvac_contractor', label: 'HVAC' },
  { value: 'electrician', label: 'Electrician' },
  { value: 'landscaper', label: 'Landscaper' },
  { value: 'lawn_care', label: 'Lawn Care' },
  { value: 'cleaning_service', label: 'Cleaning Service' },
  { value: 'pest_control', label: 'Pest Control' },
  { value: 'roofer', label: 'Roofer' },
  { value: 'painter', label: 'Painter' },
  { value: 'general_contractor', label: 'General Contractor' },
  { value: 'auto_repair', label: 'Auto Repair' },
  { value: 'dentist', label: 'Dentist' },
  { value: 'chiropractor', label: 'Chiropractor' },
  { value: 'veterinarian', label: 'Veterinarian' },
  { value: 'salon', label: 'Salon / Spa' },
  { value: 'gym', label: 'Gym / Fitness' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'insurance_agent', label: 'Insurance Agent' },
  { value: 'accountant', label: 'Accountant' },
]

function Section({ title, children }) {
  return (
    <div
      className="rounded-xl p-6"
      style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
    >
      <h2 className="text-sm font-semibold mb-4" style={{ color: 'var(--foreground)' }}>
        {title}
      </h2>
      {children}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="mb-4">
      <label className="block text-xs font-medium mb-1" style={{ color: 'var(--foreground)' }}>
        {label}
      </label>
      {hint && <p className="text-xs mb-2" style={{ color: 'var(--muted-foreground)' }}>{hint}</p>}
      {children}
    </div>
  )
}

const inputStyle = {
  width: '100%',
  background: 'var(--muted)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '8px 12px',
  color: 'var(--foreground)',
  fontSize: 13,
  outline: 'none',
}

// ── Schedule modal component ───────────────────────────────────────────────────
function ScheduleModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial ?? EMPTY_SCHEDULE_FORM)
  const [saving, setSaving] = useState(false)

  const toggleType = (val) =>
    setForm((f) => ({
      ...f,
      scan_place_types: f.scan_place_types.includes(val)
        ? f.scan_place_types.filter((v) => v !== val)
        : [...f.scan_place_types, val],
    }))

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Schedule name is required'); return }
    if (!form.scan_place_types.length) { toast.error('Select at least one industry'); return }
    setSaving(true)
    try {
      await onSave(form)
      onClose()
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.scan_place_types?.[0] || 'Failed to save'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl p-6 space-y-4"
        style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold" style={{ color: 'var(--foreground)' }}>
          {initial ? 'Edit Schedule' : 'New Schedule'}
        </h3>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--foreground)' }}>Name</label>
          <input
            style={{ ...inputStyle, width: '100%' }}
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Weekday HVAC scan"
          />
        </div>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--foreground)' }}>Frequency</label>
          <div className="grid grid-cols-2 gap-2">
            {CRON_PRESETS.map(({ label, value }) => (
              <button
                key={value}
                type="button"
                onClick={() => setForm((f) => ({ ...f, cron_expression: value }))}
                className="text-xs rounded-lg px-3 py-2 text-left transition-colors"
                style={{
                  background: form.cron_expression === value ? '#f9731620' : 'var(--muted)',
                  border: `1px solid ${form.cron_expression === value ? '#f97316' : 'var(--border)'}`,
                  color: form.cron_expression === value ? '#f97316' : 'var(--muted-foreground)',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--foreground)' }}>Industries to scan</label>
          <div className="flex flex-wrap gap-1.5">
            {PLACE_TYPE_OPTIONS.map(({ value, label }) => {
              const active = form.scan_place_types.includes(value)
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => toggleType(value)}
                  className="text-xs rounded-full px-2.5 py-1 transition-colors"
                  style={{
                    background: active ? '#f97316' : 'var(--muted)',
                    color: active ? '#fff' : 'var(--muted-foreground)',
                    border: `1px solid ${active ? '#f97316' : 'var(--border)'}`,
                  }}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--foreground)' }}>
            Radius (meters)
          </label>
          <input
            type="number"
            style={{ ...inputStyle, width: '100%' }}
            value={form.scan_radius_meters}
            onChange={(e) => setForm((f) => ({ ...f, scan_radius_meters: Number(e.target.value) }))}
            min={500}
            max={50000}
          />
        </div>

        <div className="flex gap-2 justify-end pt-2">
          <button
            onClick={onClose}
            className="text-xs px-4 py-2 rounded-lg"
            style={{ background: 'var(--muted)', color: 'var(--muted-foreground)', border: '1px solid var(--border)' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs px-4 py-2 rounded-lg font-medium"
            style={{ background: '#f97316', color: '#fff', opacity: saving ? 0.6 : 1 }}
          >
            {saving ? 'Saving…' : 'Save schedule'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AgentPage() {
  const { config, updateConfig, setPaused, isLoading, schedules, schedulesLoaded, fetchSchedules, createSchedule, updateSchedule, deleteSchedule, runNow } = useAgentStore()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [scheduleModal, setScheduleModal] = useState(null) // null | 'new' | scheduleObject

  useEffect(() => {
    if (!schedulesLoaded) fetchSchedules()
  }, [schedulesLoaded, fetchSchedules])

  useEffect(() => {
    if (config) {
      setForm({
        service_name: config.service_name ?? '',
        service_description: config.service_description ?? '',
        agent_name: config.agent_name ?? '',
        target_industries: config.target_industries ?? [],
        target_biz_description: config.target_biz_description ?? '',
        outreach_tone: config.outreach_tone ?? 'semi_formal',
        key_selling_points: config.key_selling_points?.length
          ? config.key_selling_points
          : [''],
        custom_talking_points: config.custom_talking_points ?? '',
      })
    }
  }, [config])

  if (isLoading || !form) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--muted-foreground)' }}>
        Loading…
      </div>
    )
  }

  const toggleIndustry = (val) => {
    setForm((f) => ({
      ...f,
      target_industries: f.target_industries.includes(val)
        ? f.target_industries.filter((v) => v !== val)
        : [...f.target_industries, val],
    }))
  }

  const updatePoint = (i, val) => {
    setForm((f) => {
      const pts = [...f.key_selling_points]
      pts[i] = val
      return { ...f, key_selling_points: pts }
    })
  }

  const addPoint = () => {
    if (form.key_selling_points.length >= 5) return
    setForm((f) => ({ ...f, key_selling_points: [...f.key_selling_points, ''] }))
  }

  const removePoint = (i) => {
    setForm((f) => ({ ...f, key_selling_points: f.key_selling_points.filter((_, idx) => idx !== i) }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateConfig({
        ...form,
        key_selling_points: form.key_selling_points.filter((p) => p.trim()),
      })
      toast.success('Agent settings saved')
    } catch {
      toast.error('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleTogglePause = async () => {
    try {
      await setPaused(!config.is_paused)
      toast.success(config.is_paused ? 'Agent resumed' : 'Agent paused')
    } catch {
      toast.error('Failed to update pause state')
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-lg font-semibold" style={{ color: 'var(--foreground)' }}>
            Agent Settings
          </h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
            Configure how your AI prospecting agent represents you.
          </p>
        </div>

        {/* Pause toggle */}
        <button
          onClick={handleTogglePause}
          className="flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-1.5 transition-colors"
          style={{
            background: config.is_paused ? 'var(--muted)' : '#f9731620',
            color: config.is_paused ? 'var(--muted-foreground)' : '#f97316',
            border: `1px solid ${config.is_paused ? 'var(--border)' : '#f9731640'}`,
          }}
        >
          {config.is_paused ? (
            <>
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Resume Agent
            </>
          ) : (
            <>
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16"/>
                <rect x="14" y="4" width="4" height="16"/>
              </svg>
              Pause Agent
            </>
          )}
        </button>
      </div>

      {/* Status badge */}
      {config.is_paused && (
        <div
          className="rounded-lg px-4 py-3 text-xs"
          style={{ background: '#f9731610', color: '#f97316', border: '1px solid #f9731630' }}
        >
          Agent is paused — no automated scans or outreach will run.
        </div>
      )}

      <Section title="Your Service">
        <Field label="Service name" hint="What do you sell? e.g. 'CRM automation for home services'">
          <input
            style={inputStyle}
            value={form.service_name}
            onChange={(e) => setForm((f) => ({ ...f, service_name: e.target.value }))}
            placeholder="e.g. Scheduling software for HVAC companies"
          />
        </Field>
        <Field label="Service description">
          <textarea
            style={{ ...inputStyle, minHeight: 72, resize: 'vertical' }}
            value={form.service_description}
            onChange={(e) => setForm((f) => ({ ...f, service_description: e.target.value }))}
            placeholder="Describe what your product does and the problem it solves."
          />
        </Field>
        <Field label="Agent name" hint="The name your AI agent uses when crafting outreach (optional).">
          <input
            style={inputStyle}
            value={form.agent_name}
            onChange={(e) => setForm((f) => ({ ...f, agent_name: e.target.value }))}
            placeholder="e.g. Jordan"
          />
        </Field>
      </Section>

      <Section title="Target Customers">
        <Field label="Industries" hint="Select the industries you want to prospect.">
          <div className="flex flex-wrap gap-2 mt-1">
            {COMMON_INDUSTRIES.map(({ value, label }) => {
              const active = form.target_industries.includes(value)
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => toggleIndustry(value)}
                  className="text-xs rounded-full px-3 py-1 transition-colors"
                  style={{
                    background: active ? '#f97316' : 'var(--muted)',
                    color: active ? '#fff' : 'var(--muted-foreground)',
                    border: `1px solid ${active ? '#f97316' : 'var(--border)'}`,
                  }}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </Field>
        <Field label="Additional targeting notes">
          <textarea
            style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }}
            value={form.target_biz_description}
            onChange={(e) => setForm((f) => ({ ...f, target_biz_description: e.target.value }))}
            placeholder="e.g. Focus on businesses with 2–20 employees that have a website but no online booking."
          />
        </Field>
      </Section>

      <Section title="Outreach Style">
        <Field label="Tone">
          <div className="space-y-2 mt-1">
            {TONE_OPTIONS.map(({ value, label, desc }) => (
              <label
                key={value}
                className="flex items-start gap-3 rounded-lg p-3 cursor-pointer transition-colors"
                style={{
                  background: form.outreach_tone === value ? '#f9731610' : 'var(--muted)',
                  border: `1px solid ${form.outreach_tone === value ? '#f9731640' : 'var(--border)'}`,
                }}
              >
                <input
                  type="radio"
                  name="tone"
                  value={value}
                  checked={form.outreach_tone === value}
                  onChange={() => setForm((f) => ({ ...f, outreach_tone: value }))}
                  style={{ accentColor: '#f97316', marginTop: 2, flexShrink: 0 }}
                />
                <div>
                  <div className="text-xs font-medium" style={{ color: 'var(--foreground)' }}>{label}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>{desc}</div>
                </div>
              </label>
            ))}
          </div>
        </Field>

        <Field label="Key selling points" hint="Up to 5 points your agent will highlight in outreach.">
          <div className="space-y-2 mt-1">
            {form.key_selling_points.map((pt, i) => (
              <div key={i} className="flex gap-2">
                <input
                  style={{ ...inputStyle, flex: 1 }}
                  value={pt}
                  onChange={(e) => updatePoint(i, e.target.value)}
                  placeholder={`Selling point ${i + 1}`}
                />
                {form.key_selling_points.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePoint(i)}
                    className="text-xs px-2 rounded"
                    style={{ color: 'var(--muted-foreground)', background: 'var(--muted)', border: '1px solid var(--border)' }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {form.key_selling_points.length < 5 && (
              <button
                type="button"
                onClick={addPoint}
                className="text-xs"
                style={{ color: '#f97316' }}
              >
                + Add point
              </button>
            )}
          </div>
        </Field>

        <Field label="Custom talking points" hint="Anything else the agent should know or emphasize (optional).">
          <textarea
            style={{ ...inputStyle, minHeight: 72, resize: 'vertical' }}
            value={form.custom_talking_points}
            onChange={(e) => setForm((f) => ({ ...f, custom_talking_points: e.target.value }))}
            placeholder="e.g. Mention our free 30-day trial. Avoid comparing us to competitors by name."
          />
        </Field>
      </Section>

      <div className="flex justify-end pb-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-sm font-medium rounded-lg px-5 py-2 transition-opacity"
          style={{
            background: '#f97316',
            color: '#fff',
            opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </div>

      {/* Schedules section */}
      <Section title="Scan Schedules">
        <p className="text-xs mb-4" style={{ color: 'var(--muted-foreground)' }}>
          Schedules use your agent&apos;s default location. Set a default lat/lng above to enable them.
        </p>

        {schedules.length === 0 ? (
          <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
            No schedules yet. Add one to run automated scans.
          </p>
        ) : (
          <div className="space-y-2 mb-4">
            {schedules.map((sc) => (
              <div
                key={sc.id}
                className="flex items-center justify-between rounded-lg p-3"
                style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}
              >
                <div>
                  <div className="text-xs font-medium" style={{ color: 'var(--foreground)' }}>{sc.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
                    {CRON_PRESETS.find((p) => p.value === sc.cron_expression)?.label ?? sc.cron_expression}
                    {' · '}
                    {sc.scan_place_types.slice(0, 3).join(', ')}{sc.scan_place_types.length > 3 ? ` +${sc.scan_place_types.length - 3}` : ''}
                  </div>
                  {sc.last_run_at && (
                    <div className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
                      Last ran {new Date(sc.last_run_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {/* Active toggle */}
                  <button
                    onClick={async () => {
                      try {
                        await updateSchedule(sc.id, { is_active: !sc.is_active })
                        toast.success(sc.is_active ? 'Schedule paused' : 'Schedule activated')
                      } catch { toast.error('Failed to update') }
                    }}
                    className="text-xs px-2 py-1 rounded"
                    style={{
                      background: sc.is_active ? '#22c55e20' : 'var(--muted)',
                      color: sc.is_active ? '#22c55e' : 'var(--muted-foreground)',
                      border: `1px solid ${sc.is_active ? '#22c55e40' : 'var(--border)'}`,
                    }}
                  >
                    {sc.is_active ? 'Active' : 'Paused'}
                  </button>
                  {/* Run now */}
                  <button
                    onClick={async () => {
                      try {
                        await runNow(sc.id)
                        toast.success('Scan queued')
                      } catch (err) {
                        toast.error(err?.response?.data?.detail ?? 'Failed to run')
                      }
                    }}
                    className="text-xs px-2 py-1 rounded"
                    style={{ background: 'var(--muted)', color: 'var(--muted-foreground)', border: '1px solid var(--border)' }}
                  >
                    Run now
                  </button>
                  {/* Edit */}
                  <button
                    onClick={() => setScheduleModal(sc)}
                    className="text-xs px-2 py-1 rounded"
                    style={{ background: 'var(--muted)', color: 'var(--muted-foreground)', border: '1px solid var(--border)' }}
                  >
                    Edit
                  </button>
                  {/* Delete */}
                  <button
                    onClick={async () => {
                      if (!confirm('Delete this schedule?')) return
                      try {
                        await deleteSchedule(sc.id)
                        toast.success('Schedule deleted')
                      } catch { toast.error('Failed to delete') }
                    }}
                    className="text-xs px-2 py-1 rounded"
                    style={{ color: '#ef4444', background: 'var(--muted)', border: '1px solid var(--border)' }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => setScheduleModal('new')}
          className="text-xs font-medium"
          style={{ color: '#f97316' }}
        >
          + Add schedule
        </button>
      </Section>

      <div className="pb-8" />

      {scheduleModal && (
        <ScheduleModal
          initial={scheduleModal === 'new' ? null : scheduleModal}
          onSave={async (data) => {
            if (scheduleModal === 'new') {
              await createSchedule(data)
              toast.success('Schedule created')
            } else {
              await updateSchedule(scheduleModal.id, data)
              toast.success('Schedule updated')
            }
          }}
          onClose={() => setScheduleModal(null)}
        />
      )}
    </div>
  )
}
