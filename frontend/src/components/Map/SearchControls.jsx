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
  const { setSearchCenter, setSearchRadius, loadMarkersForScan, clearMarkers } = useMapStore()

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

    if (!selectedCoords) {
      alert('Please select a location from the dropdown.')
      return
    }

    const [lng, lat] = selectedCoords
    setSearchCenter([lng, lat])
    setSearchRadius(radius)
    clearMarkers()

    await launchScan({
      center_lat: lat,
      center_lng: lng,
      radius_meters: radius,
      place_types: selectedTypes,
      keyword,
      label: label || `${location} — ${selectedTypes.join(', ')}`,
    })
  }

  const isRunning = activeScan && !['completed', 'failed'].includes(activeScan.status)

  return (
    <form onSubmit={handleScan} className="flex flex-col gap-3">
      <div ref={wrapperRef} className="relative">
        <label className="block text-xs font-medium text-slate-400 mb-1">Location</label>
        <input
          type="text"
          value={location}
          onChange={handleLocationChange}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          placeholder="Hernando, MS"
          autoComplete="off"
          className="w-full px-3 py-2 rounded bg-slate-700 text-slate-100 text-sm placeholder-slate-500 border border-slate-600 focus:border-blue-500 focus:outline-none"
        />
        {showSuggestions && suggestions.length > 0 && (
          <ul className="absolute z-50 left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded shadow-lg overflow-hidden">
            {suggestions.map((prediction) => (
              <li
                key={prediction.place_id}
                onMouseDown={() => handleSelectSuggestion(prediction)}
                className="px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 cursor-pointer truncate"
              >
                {prediction.description}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1">Radius</label>
        <select
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="w-full px-3 py-2 rounded bg-slate-700 text-slate-100 text-sm border border-slate-600 focus:border-blue-500 focus:outline-none"
        >
          {RADIUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2">Business Types</label>
        <div className="flex flex-wrap gap-1">
          {PLACE_TYPES.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => toggleType(type.value)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                selectedTypes.includes(type.value)
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1">Keyword (optional)</label>
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="24 hour, emergency..."
          className="w-full px-3 py-2 rounded bg-slate-700 text-slate-100 text-sm placeholder-slate-500 border border-slate-600 focus:border-blue-500 focus:outline-none"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1">Scan Label (optional)</label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="LA Plumbers Q1"
          className="w-full px-3 py-2 rounded bg-slate-700 text-slate-100 text-sm placeholder-slate-500 border border-slate-600 focus:border-blue-500 focus:outline-none"
        />
      </div>

      <button
        type="submit"
        disabled={isLaunching || isRunning || !location || selectedTypes.length === 0}
        className="w-full py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold text-sm transition-colors"
      >
        {isLaunching || isRunning ? 'Scanning...' : 'Start Scan'}
      </button>
    </form>
  )
}
