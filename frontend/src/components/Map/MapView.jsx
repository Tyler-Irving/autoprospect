import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import * as turf from '@turf/turf'
import { useMapStore } from '../../store/mapStore'
import { getScoreColor } from '../../utils/constants'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

export default function MapView() {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])

  const {
    mapCenter,
    mapZoom,
    searchCenter,
    searchRadiusMeters,
    markers,
    setSelectedBusiness,
    setHoveredBusiness,
  } = useMapStore()

  // Initialize map
  useEffect(() => {
    if (mapRef.current) return
    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: mapCenter,
      zoom: mapZoom,
    })
    map.addControl(new mapboxgl.NavigationControl(), 'top-right')
    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Draw radius circle and fly to search center when it changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const apply = () => {
      if (!searchCenter) {
        if (map.getLayer('radius-fill')) map.removeLayer('radius-fill')
        if (map.getLayer('radius-line')) map.removeLayer('radius-line')
        if (map.getSource('radius')) map.removeSource('radius')
        return
      }

      const circle = turf.circle(searchCenter, searchRadiusMeters / 1000, {
        steps: 64,
        units: 'kilometers',
      })

      if (map.getSource('radius')) {
        map.getSource('radius').setData(circle)
      } else {
        map.addSource('radius', { type: 'geojson', data: circle })
        map.addLayer({
          id: 'radius-fill',
          type: 'fill',
          source: 'radius',
          paint: { 'fill-color': '#3b82f6', 'fill-opacity': 0.08 },
        })
        map.addLayer({
          id: 'radius-line',
          type: 'line',
          source: 'radius',
          paint: { 'line-color': '#3b82f6', 'line-width': 2, 'line-dasharray': [2, 2] },
        })
      }

      map.flyTo({ center: searchCenter, zoom: 12 })
    }

    if (map.isStyleLoaded()) {
      apply()
    } else {
      map.once('style.load', apply)
    }
  }, [searchCenter, searchRadiusMeters])

  // Render business markers
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Clear existing markers
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []

    markers.forEach((business) => {
      // Outer el is the Mapbox anchor — never apply transform here or it breaks positioning.
      const el = document.createElement('div')
      el.style.cssText = 'width: 16px; height: 16px; cursor: pointer;'

      // Inner dot gets the visual styles and hover scale.
      const dot = document.createElement('div')
      dot.style.cssText = `
        width: 12px; height: 12px;
        margin: 2px;
        border-radius: 50%;
        background: ${getScoreColor(business.overall_score)};
        border: 2px solid rgba(255,255,255,0.7);
        transition: transform 0.15s;
      `
      el.appendChild(dot)
      el.addEventListener('mouseenter', () => {
        dot.style.transform = 'scale(1.5)'
        const rect = el.getBoundingClientRect()
        const cardWidth = 320
        const cardHeight = 340 // conservative estimate
        const x =
          rect.right + 8 + cardWidth > window.innerWidth
            ? rect.left - 8 - cardWidth
            : rect.right + 8
        const y = Math.max(8, Math.min(rect.top - 20, window.innerHeight - cardHeight - 8))
        setHoveredBusiness(business, { x, y })
      })
      el.addEventListener('mouseleave', () => {
        dot.style.transform = 'scale(1)'
        setHoveredBusiness(null, null)
      })

      const marker = new mapboxgl.Marker(el)
        .setLngLat([parseFloat(business.longitude ?? business.lng), parseFloat(business.latitude ?? business.lat)])
        .addTo(map)

      el.addEventListener('click', () => setSelectedBusiness(business))
      markersRef.current.push(marker)
    })
  }, [markers, setSelectedBusiness, setHoveredBusiness])

  return (
    <div ref={mapContainer} className="w-full h-full" style={{ minHeight: '400px' }} />
  )
}
