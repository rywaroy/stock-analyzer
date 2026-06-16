export const horizonLabels: Record<string, string> = {
  short_term: '短期',
  medium_term: '中期',
  long_term: '长期',
};

export function formatNumber(value: unknown, digits = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  return numeric.toLocaleString('zh-CN', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function formatCompact(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  if (Math.abs(numeric) >= 100000000) {
    return `${formatNumber(numeric / 100000000, 2)} 亿`;
  }
  if (Math.abs(numeric) >= 10000) {
    return `${formatNumber(numeric / 10000, 2)} 万`;
  }
  return formatNumber(numeric, 2);
}

export function formatPercent(value: unknown, digits = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  return `${formatNumber(numeric, digits)}%`;
}

export function formatScore(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  return `${Math.round(numeric)}`;
}

export function signalTone(signal?: string | null, score?: number | null) {
  if (signal?.includes('强买') || signal?.includes('买入')) {
    return 'positive';
  }
  if (signal?.includes('卖出') || signal?.includes('强卖') || signal?.includes('回避')) {
    return 'negative';
  }
  const numeric = Number(score);
  if (Number.isFinite(numeric)) {
    if (numeric >= 15) return 'positive';
    if (numeric <= -15) return 'negative';
  }
  return 'neutral';
}

export function scoreWidth(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '50%';
  }
  return `${Math.max(0, Math.min(100, (numeric + 100) / 2))}%`;
}

export function queryParam(name: string) {
  if (typeof window === 'undefined') {
    return '';
  }
  return new URL(window.location.href).searchParams.get(name) || '';
}
