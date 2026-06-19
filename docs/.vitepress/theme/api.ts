const apiBase = import.meta.env.VITE_STOCK_API_BASE || '';

async function request(path: string) {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `请求失败：${response.status}`);
  }
  return response.json();
}

export function fetchDates() {
  return request('/api/dates');
}

export function fetchAnalysis(date?: string) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  return request(`/api/analysis${query}`);
}

export function fetchAiEtfDates() {
  return request('/api/ai-etf/dates');
}

export function fetchAiEtf(date?: string) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  return request(`/api/ai-etf${query}`);
}

export function fetchStockDetail(stockCode: string, date?: string) {
  const params = new URLSearchParams();
  if (date) {
    params.set('date', date);
  }
  const suffix = params.toString() ? `?${params}` : '';
  return request(`/api/stocks/${encodeURIComponent(stockCode)}${suffix}`);
}
