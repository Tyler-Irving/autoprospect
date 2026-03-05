export const SCORE_THRESHOLDS = {
  LOW: { max: 39, label: 'Low', color: '#ef4444' },
  MEDIUM: { max: 69, label: 'Medium', color: '#eab308' },
  HIGH: { max: 100, label: 'High', color: '#22c55e' },
}

// Type values must match Google Places API (New) Table A supported types.
// Ref: https://developers.google.com/maps/documentation/places/web-service/place-types
export const PLACE_TYPES = [
  { value: 'plumber', label: 'Plumber' },
  { value: 'electrician', label: 'Electrician' },
  { value: 'dentist', label: 'Dentist' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'general_contractor', label: 'HVAC / Contractor' },
  { value: 'roofing_contractor', label: 'Roofing' },
  { value: 'painter', label: 'Painter' },
  { value: 'landscaping_service', label: 'Landscaper' },
  { value: 'car_repair', label: 'Auto Repair' },
  { value: 'veterinary_care', label: 'Veterinarian' },
  { value: 'beauty_salon', label: 'Beauty Salon' },
  { value: 'gym', label: 'Gym' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'real_estate_agency', label: 'Real Estate' },
  { value: 'insurance_agency', label: 'Insurance' },
]

export const SCAN_POLL_INTERVAL_MS = 3000

export const SCAN_TERMINAL_STATUSES = ['completed', 'failed']

export const getScoreColor = (score) => {
  if (score === null || score === undefined) return '#94a3b8'
  if (score <= 39) return SCORE_THRESHOLDS.LOW.color
  if (score <= 69) return SCORE_THRESHOLDS.MEDIUM.color
  return SCORE_THRESHOLDS.HIGH.color
}

export const getScoreLabel = (score) => {
  if (score === null || score === undefined) return 'Unscored'
  if (score <= 39) return 'Low'
  if (score <= 69) return 'Medium'
  return 'High'
}
