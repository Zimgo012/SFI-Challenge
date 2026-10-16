const id = encodeURIComponent

// Paths are relative to the dispatcher origin, including the /api prefix.
export const endpoints = {
  loads: {
    list: '/api/loads',
    webSocket: '/api/loads/ws',
    detail: (externalId: string) => `/api/loads/${id(externalId)}`,
    costPreview: (externalId: string) => `/api/loads/${id(externalId)}/cost-preview`,
    evaluate: (externalId: string) => `/api/loads/${id(externalId)}/evaluate`,
    accept: (externalId: string) => `/api/loads/${id(externalId)}/accept`,
    decline: (externalId: string) => `/api/loads/${id(externalId)}/decline`,
    bid: (externalId: string) => `/api/loads/${id(externalId)}/bid`,
  },
  bids: '/api/bids',
  oldestBids: '/api/bids/oldest',
  terminals: {
    list: '/api/terminals',
    detail: (code: string) => `/api/terminals/${id(code)}`,
    status: '/api/terminals/status',
    statusWebSocket: '/api/terminals/status/ws',
  },
  fleet: {
    units: '/api/fleet/units',
    projections: '/api/fleet/projections',
    projection: (unitId: string) => `/api/fleet/units/${id(unitId)}/projection`,
    unit: (unitId: string) => `/api/fleet/units/${id(unitId)}`,
    capacity: '/api/fleet/capacity',
    legacyCapacity: '/fleet/capacity',
  },
  shipments: '/api/shipments',
  oldestShipments: '/api/shipments/oldest',
  activity: '/api/activity',
  oldestActivity: '/api/activity/oldest',
  overview: '/api/overview',
  systemStatus: '/api/system/status',
  simulationClock: '/__simulation/clock',
  orderExpiration: (externalId: string) => `/orders/${id(externalId)}/expiration`,
  health: '/health',
} as const
