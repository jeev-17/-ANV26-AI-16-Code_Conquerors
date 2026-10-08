import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 90000 })

const errMsg = (e) =>
  e.response?.data?.detail
    ? typeof e.response.data.detail === 'string' ? e.response.data.detail : JSON.stringify(e.response.data.detail)
    : e.code === 'ERR_NETWORK' ? 'Cannot reach the SafeRouteAI backend. Is it running on port 8000?' : e.message

const wrap = (p) => p.then((r) => r.data).catch((e) => { throw new Error(errMsg(e)) })

export const getRouteRisk = (start, end) => wrap(http.post('/route-risk', { start, end }))
export const explain = (analysis_id, route_index, segment_id) =>
  wrap(http.post('/explain', { analysis_id, route_index, segment_id: segment_id || null }))
export const getModelInfo = () => wrap(http.get('/model-info'))
export const getHealth = () => wrap(http.get('/health'))
