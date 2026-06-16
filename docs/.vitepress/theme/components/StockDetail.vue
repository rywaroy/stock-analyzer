<script setup lang="ts">
import MarkdownIt from 'markdown-it';
import { computed, onMounted, ref } from 'vue';
import { fetchDates, fetchStockDetail } from '../api';
import {
  formatCompact,
  formatNumber,
  formatPercent,
  formatScore,
  horizonLabels,
  queryParam,
} from '../formatters';
import EChart from './EChart.vue';
import ScoreBar from './ScoreBar.vue';
import SignalBadge from './SignalBadge.vue';

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});

const dates = ref<any[]>([]);
const payload = ref<any | null>(null);
const loading = ref(true);
const error = ref('');
const stockCode = ref('');
const tradeDate = ref('');

const detail = computed(() => payload.value?.detail || null);
const reportHtml = computed(() => (detail.value?.report?.text ? md.render(detail.value.report.text) : ''));
const historyRows = computed(() => payload.value?.history || []);
const trendWindows = computed(() => payload.value?.trendWindows || []);
const accuracySummary = computed(() => payload.value?.accuracySummary || []);

const historyChartOptions = computed(() => ({
  color: ['#111827', '#dc2626', '#2563eb', '#16a34a'],
  tooltip: { trigger: 'axis' },
  legend: { top: 0, data: ['总分', '短期', '中期', '长期'] },
  grid: { left: 42, right: 18, top: 48, bottom: 32 },
  xAxis: {
    type: 'category',
    data: historyRows.value.map((item: any) => item.tradeDate),
    axisLabel: { color: '#64748b' },
  },
  yAxis: {
    type: 'value',
    min: -100,
    max: 100,
    axisLabel: { color: '#64748b' },
    splitLine: { lineStyle: { color: '#e5e7eb' } },
  },
  series: [
    { name: '总分', type: 'line', smooth: true, data: historyRows.value.map((item: any) => item.score) },
    { name: '短期', type: 'line', smooth: true, data: historyRows.value.map((item: any) => item.shortTermScore) },
    { name: '中期', type: 'line', smooth: true, data: historyRows.value.map((item: any) => item.mediumTermScore) },
    { name: '长期', type: 'line', smooth: true, data: historyRows.value.map((item: any) => item.longTermScore) },
  ],
}));

const trendWindowChartOptions = computed(() => ({
  color: ['#2563eb', '#16a34a', '#f59e0b', '#7c3aed'],
  tooltip: { trigger: 'axis' },
  legend: { top: 0, data: ['窗口涨跌幅', '相对均线', 'MACD 正柱占比', 'BOLL 中轨上方占比'] },
  grid: { left: 42, right: 18, top: 52, bottom: 32 },
  xAxis: {
    type: 'category',
    data: trendWindows.value.map((item: any) => `${item.windowDays}日`),
    axisLabel: { color: '#64748b' },
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: '{value}%', color: '#64748b' },
    splitLine: { lineStyle: { color: '#e5e7eb' } },
  },
  series: [
    { name: '窗口涨跌幅', type: 'bar', data: trendWindows.value.map((item: any) => item.returnPct) },
    { name: '相对均线', type: 'bar', data: trendWindows.value.map((item: any) => item.closeVsMaPct) },
    {
      name: 'MACD 正柱占比',
      type: 'line',
      smooth: true,
      data: trendWindows.value.map((item: any) => Number(item.macdPositiveRatio) * 100),
    },
    {
      name: 'BOLL 中轨上方占比',
      type: 'line',
      smooth: true,
      data: trendWindows.value.map((item: any) => Number(item.bollMidAboveRatio) * 100),
    },
  ],
}));

function listHref(date: string) {
  return `/?date=${encodeURIComponent(date)}`;
}

function horizonEntries(scores: Record<string, any>) {
  return ['short_term', 'medium_term', 'long_term']
    .map((key) => ({ key, ...(scores?.[key] || {}) }))
    .filter((item) => item.score !== undefined || item.parts?.length);
}

async function loadDetail() {
  loading.value = true;
  error.value = '';
  try {
    stockCode.value = queryParam('code');
    tradeDate.value = queryParam('date');
    if (!stockCode.value) {
      throw new Error('缺少股票代码');
    }
    const [datePayload, detailPayload] = await Promise.all([
      fetchDates(),
      fetchStockDetail(stockCode.value, tradeDate.value || undefined),
    ]);
    dates.value = datePayload.dates || [];
    payload.value = detailPayload;
    tradeDate.value = detailPayload.detail?.tradeDate || tradeDate.value;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadDetail();
});
</script>

<template>
  <div class="stock-shell">
    <aside class="stock-sidebar">
      <div class="stock-sidebar__title">交易日</div>
      <a
        v-for="date in dates"
        :key="date.tradeDate"
        class="date-item"
        :class="{ 'date-item--active': date.tradeDate === tradeDate }"
        :href="listHref(date.tradeDate)"
      >
        <span>{{ date.tradeDate }}</span>
        <small>{{ date.stockCount }} 只</small>
      </a>
    </aside>

    <main class="stock-main">
      <div v-if="error" class="stock-alert">{{ error }}</div>
      <div v-else-if="loading" class="stock-empty">加载中...</div>

      <template v-else-if="detail">
        <div class="stock-title-row">
          <div>
            <p class="stock-kicker">{{ detail.tradeDate }} · {{ detail.regime || '状态暂无' }}</p>
            <h2>{{ detail.displayName }}</h2>
          </div>
          <a class="back-link" :href="listHref(detail.tradeDate)">返回列表</a>
        </div>

        <section class="detail-hero">
          <div>
            <span>总分</span>
            <strong>{{ formatScore(detail.score) }}</strong>
            <SignalBadge :signal="detail.signalLabel" :score="detail.score" />
          </div>
          <p>{{ detail.advice || '暂无操作建议' }}</p>
        </section>

        <section class="metric-grid metric-grid--four">
          <div class="metric-card">
            <span>置信度</span>
            <strong>{{ detail.confidence || '暂无' }}</strong>
          </div>
          <div class="metric-card">
            <span>收盘价</span>
            <strong>{{ formatNumber(detail.quote.closePrice, 4) }}</strong>
          </div>
          <div class="metric-card">
            <span>成交额</span>
            <strong>{{ formatCompact(detail.quote.amount) }}</strong>
          </div>
          <div class="metric-card">
            <span>换手率</span>
            <strong>{{ formatPercent(detail.quote.turnoverRate) }}</strong>
          </div>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>历史得分</h3>
            <span>{{ historyRows.length }} 个样本</span>
          </div>
          <EChart :options="historyChartOptions" height="320px" />
        </section>

        <section class="horizon-grid">
          <article v-for="item in horizonEntries(detail.horizonScores)" :key="item.key" class="horizon-card">
            <div class="horizon-card__head">
              <h3>{{ horizonLabels[item.key] }}</h3>
              <SignalBadge :signal="item.signal" :score="item.score" />
            </div>
            <ScoreBar :label="`${horizonLabels[item.key]}评分`" :score="item.score" :signal="item.signal" />
            <p>{{ item.advice || '暂无建议' }}</p>
            <ul>
              <li v-for="part in item.parts || []" :key="`${item.key}-${part.module}`">
                <strong>{{ part.module }} {{ formatNumber(part.points, 1) }}</strong>
                <span>{{ part.reason }}</span>
              </li>
            </ul>
          </article>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>评分拆解</h3>
            <span>{{ detail.scoreParts.length }} 项</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>模块</th>
                  <th>分值</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="part in detail.scoreParts" :key="`${part.module}-${part.reason}`">
                  <td>{{ part.module }}</td>
                  <td>{{ formatNumber(part.points, 1) }}</td>
                  <td>{{ part.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>技术与趋势窗口</h3>
            <span>{{ detail.trend.rating || '趋势暂无' }}</span>
          </div>
          <p class="panel-summary">{{ detail.trend.conclusion || '暂无趋势结论' }}</p>
          <EChart v-if="trendWindows.length" :options="trendWindowChartOptions" height="320px" />
          <div class="data-grid">
            <div><span>MA20</span><strong>{{ formatNumber(detail.technical.ma20, 4) }}</strong></div>
            <div><span>MA60</span><strong>{{ formatNumber(detail.technical.ma60, 4) }}</strong></div>
            <div><span>MACD 柱</span><strong>{{ formatNumber(detail.technical.macdBar, 6) }}</strong></div>
            <div><span>BOLL</span><strong>{{ detail.technical.bollPosition || '暂无' }}</strong></div>
            <div><span>KDJ-J</span><strong>{{ formatNumber(detail.technical.kdjJ, 2) }}</strong></div>
            <div><span>RSI6</span><strong>{{ formatNumber(detail.technical.rsi6, 2) }}</strong></div>
            <div><span>RSI24</span><strong>{{ formatNumber(detail.technical.rsi24, 2) }}</strong></div>
            <div><span>量比5</span><strong>{{ formatNumber(detail.technical.volumeRatio5, 2) }}</strong></div>
          </div>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>基本面</h3>
            <span>{{ payload.financial?.reportDate || '财报期暂无' }}</span>
          </div>
          <div class="data-grid">
            <div><span>ROE</span><strong>{{ formatPercent(payload.financial?.roe) }}</strong></div>
            <div><span>营收增长</span><strong>{{ formatPercent(payload.financial?.revenueGrowth) }}</strong></div>
            <div><span>净利增长</span><strong>{{ formatPercent(payload.financial?.netProfitGrowth) }}</strong></div>
            <div><span>资产负债率</span><strong>{{ formatPercent(payload.financial?.debtRatio) }}</strong></div>
            <div><span>每股收益</span><strong>{{ formatNumber(payload.financial?.eps, 4) }}</strong></div>
            <div><span>经营现金流/净利润</span><strong>{{ formatNumber(payload.financial?.ocfToProfit, 4) }}</strong></div>
          </div>
        </section>

        <section class="two-column">
          <article class="stock-panel">
            <div class="section-head">
              <h3>优势观察</h3>
              <span>{{ detail.report.json?.strengths?.length || 0 }} 条</span>
            </div>
            <ul class="plain-list">
              <li v-for="item in detail.report.json?.strengths || []" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="stock-panel">
            <div class="section-head">
              <h3>风险观察</h3>
              <span>{{ detail.report.json?.risks?.length || 0 }} 条</span>
            </div>
            <ul class="plain-list">
              <li v-for="item in detail.report.json?.risks || []" :key="item">{{ item }}</li>
            </ul>
          </article>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>历史验证</h3>
            <span>{{ accuracySummary.length }} 个窗口</span>
          </div>
          <div v-if="accuracySummary.length" class="accuracy-grid">
            <div v-for="item in accuracySummary" :key="`${item.horizon}-${item.windowDays}`">
              <span>{{ horizonLabels[item.horizon] }} {{ item.windowDays }}日</span>
              <strong>{{ formatPercent(item.hitRatePct) }}</strong>
              <small>样本 {{ item.sampleCount }} · 平均收益 {{ formatPercent(item.avgReturnPct) }}</small>
            </div>
          </div>
          <p v-else class="panel-summary">暂无已到期历史验证样本，先持续积累。</p>
        </section>

        <section v-if="detail.sourceErrors.length" class="stock-panel stock-panel--warning">
          <div class="section-head">
            <h3>数据提醒</h3>
            <span>{{ detail.sourceErrors.length }} 条</span>
          </div>
          <ul class="plain-list">
            <li v-for="item in detail.sourceErrors" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section class="stock-panel">
          <div class="section-head">
            <h3>最终报告</h3>
            <span>{{ detail.report.title || 'final_summary' }}</span>
          </div>
          <div class="report-body" v-html="reportHtml" />
        </section>
      </template>
    </main>
  </div>
</template>
