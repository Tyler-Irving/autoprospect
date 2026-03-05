# Frontend — CLAUDE.md

## Project Structure

```
frontend/src/
├── App.jsx              # Router + layout shell
├── main.jsx             # Entry point
├── api/                 # Axios client + endpoint modules (scans.js, businesses.js, leads.js)
├── components/
│   ├── Map/             # MapView, SearchControls, RadiusOverlay, BusinessMarker
│   ├── Dashboard/       # LeadTable, LeadDetail, ScoreCard, FilterBar, StatsOverview
│   ├── Scan/            # ScanLauncher, ScanProgress, ScanHistory
│   ├── Outreach/        # EmailPreview, CallScriptPreview, OutreachGenerator
│   └── common/          # Sidebar, TopBar, LoadingStates
├── hooks/               # useScans, useBusinesses, useLeads
├── store/               # Zustand stores: scanStore, mapStore, leadStore
└── utils/               # formatters.js, constants.js
```

## Key Technical Choices

- **Mapbox GL JS** for the map (NOT react-map-gl wrapper unless it simplifies things meaningfully)
- **Zustand** for state management — one store per domain (scan, map, leads)
- **Axios** for API calls with a shared instance configured with baseURL and interceptors
- **React Router v6** for routing
- **Tailwind CSS** for styling — utility-first, no custom CSS files unless truly necessary
- **Vite** for bundling — no webpack, no CRA

## Component Conventions

- Functional components only. No class components.
- Props: destructure in function signature. Provide PropTypes or TypeScript types.
- State: local `useState` for UI-only state. Zustand for shared/persistent state.
- Side effects: `useEffect` for data fetching on mount. Custom hooks for reusable logic.
- Files: one component per file. Name matches component. Colocate styles if needed.

## Map Integration Patterns

- Mapbox access token from `import.meta.env.VITE_MAPBOX_TOKEN`
- Business markers color-coded by score: red (0-39), yellow (40-69), green (70-100)
- Radius circle overlay uses `turf.js` circle → GeoJSON source
- Use lightweight `/api/businesses/map-data/` endpoint for markers (id, name, lat, lng, score only)
- Cluster markers at low zoom using Mapbox's built-in clustering

## API Communication

- Base URL: `import.meta.env.VITE_API_URL` (defaults to `http://localhost:8000/api`)
- Scan progress: poll `GET /api/scans/{id}/` every 3 seconds while `status !== "completed"`
- All mutating requests (POST, PATCH, DELETE) should show loading state and handle errors with toast notifications
- Never cache business data across scans — always refetch after scan completes

## Score Display Conventions

- Overall score: circular gauge or large number with color background
- Sub-scores (CRM, scheduling, marketing, invoicing): horizontal progress bars
- Key signals: rendered as colored chips/badges
- Score thresholds: 0-39 = "Low" (red), 40-69 = "Medium" (yellow), 70-100 = "High" (green)

## Common Gotchas

- Mapbox GL JS requires the CSS import: `import 'mapbox-gl/dist/mapbox-gl.css'`
- Mapbox `map.on('load')` must fire before adding sources/layers
- Zustand stores should use `immer` middleware if you need nested state updates
- Vite env vars must be prefixed with `VITE_` to be exposed to client code
- CORS: backend must include `http://localhost:5173` in `CORS_ALLOWED_ORIGINS`
