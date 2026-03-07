import { useState, useEffect, useRef } from 'react'
import client from '../../api/client'
import { useScanStore } from '../../store/scanStore'
import { useMapStore } from '../../store/mapStore'
import { PLACE_TYPES } from '../../utils/constants'

const RADIUS_OPTIONS = [
  { value: 1609, label: '1 mile' },
  { value: 4023, label: '2.5 miles' },
  { value: 8047, label: '5 miles' },
  { value: 16093, label: '10 miles' },
  { value: 24140, label: '15 miles' },
]

export default function SearchControls() {
  const { launchScan, isLaunching, activeScan } = useScanStore()
  const { setSearchCenter, setSearchRadius, loadMarkersForScan, clearMarkers, mapClickCenter, setMapClickCenter } = useMapStore()

  const [location, setLocation] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [selectedCoords, setSelectedCoords] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [radius, setRadius] = useState(8047)
  const [selectedTypes, setSelectedTypes] = useState(['plumber'])
  const [keyword, setKeyword] = useState('')
  const [label, setLabel] = useState('')
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  // Load markers as soon as the active scan completes — no polling interval needed.
  useEffect(() => {
    if (activeScan?.status === 'completed') {
      loadMarkersForScan(activeScan.id)
    }
  }, [activeScan?.status, activeScan?.id])

  // React to map clicks — reverse geocode the clicked coordinates into a place name.
  useEffect(() => {
    if (!mapClickCenter) return
    const [lng, lat] = mapClickCenter
    const fallback = `${lat.toFixed(4)}\u00b0 N, ${Math.abs(lng).toFixed(4)}\u00b0 W`
    const token = import.meta.env.VITE_MAPBOX_TOKEN

    const namePromise = token
      ? fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?types=place,locality,neighborhood,district&access_token=${token}`
        )
          .then((r) => r.json())
          .then((data) => data.features?.[0]?.place_name || fallback)
          .catch(() => fallback)
      : Promise.resolve(fallback)

    namePromise.then((name) => setLocation(name))
  }, [mapClickCenter])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const fetchSuggestions = (query) => {
    if (query.length < 2) {
      setSuggestions([])
      return
    }
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const { data } = await client.get('/places/autocomplete/', { params: { input: query } })
        setSuggestions(data.predictions || [])
        setShowSuggestions(true)
      } catch {
        setSuggestions([])
      }
    }, 300)
  }

  const handleLocationChange = (e) => {
    const val = e.target.value
    setLocation(val)
    setSelectedCoords(null)
    setMapClickCenter(null)
    fetchSuggestions(val)
  }

  const handleSelectSuggestion = async (prediction) => {
    setLocation(prediction.description)
    setSuggestions([])
    setShowSuggestions(false)
    try {
      const { data } = await client.get('/places/geocode/', { params: { place_id: prediction.place_id } })
      setSelectedCoords([data.lng, data.lat])
    } catch {
      setSelectedCoords(null)
    }
  }

  const toggleType = (type) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    )
  }

  const handleScan = async (e) => {
    e.preventDefault()
    if (!location || selectedTypes.length === 0) return

    const effectiveCoords = selectedCoords || mapClickCenter
    if (!effectiveCoords) return

    const [lng, lat] = effectiveCoords
    setSearchCenter([lng, lat])
    setSearchRadius(radius)
    clearMarkers()

    await launchScan({
      center_lat: parseFloat(lat.toFixed(7)),
      center_lng: parseFloat(lng.toFixed(7)),
      radius_meters: radius,
      place_types: selectedTypes,
      keyword,
      label: label || `${location} — ${selectedTypes.join(', ')}`,
    })
  }

  const isRunning = activeScan && !['completed', 'failed'].includes(activeScan.status)

  const inputStyle = {
    background: 'var(--secondary)',
    color: 'var(--foreground)',
    border: '1px solid var(--border)',
  }

  const inputClass = 'w-full h-9 px-3 rounded text-sm focus:outline-none transition-colors'

  return (
    <form onSubmit={handleScan} className="flex flex-col gap-3">

      {/* Location */}
      <div ref={wrapperRef} className="relative">
        <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
          Location
        </label>
        <div className="relative">
          {/* Search icon */}
          <svg
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2"
            width="13" height="13" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            viewBox="0 0 24 24" style={{ color: 'var(--muted-foreground)' }}
          >
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            value={location}
            onChange={handleLocationChange}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            placeholder="City, neighborhood — or click map"
            autoComplete="off"
            className={inputClass}
            style={{ ...inputStyle, paddingLeft: '2rem' }}
          />
          {/* Resolved indicator */}
          {(selectedCoords || mapClickCenter) && (
            <span
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full"
              style={{ background: '#f97316' }}
            />
          )}
        </div>
        {/* Autocomplete dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <ul
            className="absolute z-50 left-0 right-0 mt-1 rounded overflow-hidden"
            style={{ background: 'var(--popover)', border: '1px solid var(--border)', boxShadow: '0 8px 24px rgba(0,0,0,.5)' }}
          >
            {suggestions.map((prediction) => (
              <li
                key={prediction.place_id}
                onMouseDown={() => handleSelectSuggestion(prediction)}
                className="px-3 py-2 text-xs cursor-pointer truncate transition-colors"
                style={{ color: 'var(--foreground)', borderBottom: '1px solid var(--border)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--accent)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                {prediction.description}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Radius */}
      <div>
        <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
          Radius
        </label>
        <select
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className={inputClass}
          style={inputStyle}
        >
          {RADIUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Business Types */}
      <div>
        <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
          Business Types
        </label>
        <div className="flex flex-wrap gap-1.5">
          {PLACE_TYPES.map((type) => {
            const active = selectedTypes.includes(type.value)
            return (
              <button
                key={type.value}
                type="button"
                onClick={() => toggleType(type.value)}
                className="px-2.5 py-1 rounded-full text-xs font-medium transition-all cursor-pointer"
                style={
                  active
                    ? { background: '#f97316', color: '#fff', border: '1px solid #f97316' }
                    : { background: 'var(--secondary)', color: 'var(--muted-foreground)', border: '1px solid var(--border)' }
                }
              >
                {type.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Optional fields — visually separated */}
      <div className="flex flex-col gap-3 pt-1" style={{ borderTop: '1px solid var(--border)' }}>
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
            Keyword <span style={{ color: 'var(--muted-foreground)', fontWeight: 400, opacity: 0.6 }}>— optional</span>
          </label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="emergency, 24 hour…"
            className={inputClass}
            style={inputStyle}
          />
        </div>

        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
            Scan Label <span style={{ color: 'var(--muted-foreground)', fontWeight: 400, opacity: 0.6 }}>— optional</span>
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Hernando Plumbers Q1"
            className={inputClass}
            style={inputStyle}
          />
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLaunching || isRunning || !location || !(selectedCoords || mapClickCenter) || selectedTypes.length === 0}
        className="w-full h-9 rounded text-sm font-semibold text-white transition-all cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
        style={{ background: (isLaunching || isRunning) ? '#c2510f' : '#f97316' }}
      >
        {isLaunching || isRunning ? 'Scanning…' : 'Start Scan'}
      </button>

      {/* No-coords hint */}
      {location && !(selectedCoords || mapClickCenter) && !isRunning && (
        <p className="text-[11px] text-center" style={{ color: 'var(--muted-foreground)' }}>
          Select a suggestion or click the map
        </p>
      )}
    </form>
  )
}
