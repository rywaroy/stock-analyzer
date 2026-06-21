<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { BarChartOutlined, RightOutlined } from '@ant-design/icons-vue';
import { fetchAnalysis, fetchDates } from '../api';
import { formatCompact, formatNumber, formatScore, formatPercent, queryParam } from '../formatters';

type DateSummary = {
  tradeDate: string;
  stockCount: number;
  avgScore: number | null;
  maxScore: number | null;
  minScore: number | null;
  buyBiasCount: number;
  watchCount: number;
  sellBiasCount: number;
  highConfidenceCount: number;
  sourceErrorCount: number;
  updatedAt: string;
};

const dates = ref<DateSummary[]>([]);
const selectedDate = ref('');
const summary = ref<DateSummary | null>(null);
const items = ref<any[]>([]);
const loading = ref(true);
const error = ref('');

const columns = [
  { title: '股票', key: 'stock', width: 180, fixed: 'left' },
  { title: '总分', key: 'score', width: 96, sorter: (a: any, b: any) => Number(a.score) - Number(b.score) },
  { title: '信号', key: 'signal', width: 112 },
  { title: '短期', key: 'shortTerm', width: 112, sorter: (a: any, b: any) => Number(a.shortTermScore) - Number(b.shortTermScore) },
  { title: '中期', key: 'mediumTerm', width: 112, sorter: (a: any, b: any) => Number(a.mediumTermScore) - Number(b.mediumTermScore) },
  { title: '长期', key: 'longTerm', width: 112, sorter: (a: any, b: any) => Number(a.longTermScore) - Number(b.longTermScore) },
  { title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 92 },
  { title: '结论', key: 'conclusion', width: 220, ellipsis: true },
  { title: '收盘 / 换手', key: 'quote', width: 150 },
  { title: '成交额', key: 'amount', width: 120 },
  { title: '趋势', key: 'trend', ellipsis: true },
  { title: '数据', key: 'dataStatus', width: 118 },
  { title: '', key: 'action', width: 88, fixed: 'right' },
];

const tableRows = computed(() =>
  items.value.map((item) => ({
    ...item,
    key: `${item.stockCode}-${item.tradeDate}`,
  })),
);

const pagination = computed(() =>
  tableRows.value.length > 20
    ? {
        pageSize: 20,
        showSizeChanger: true,
        showTotal: (total: number) => `共 ${total} 条`,
      }
    : false,
);

function detailHref(item: any) {
  return `/analysis/detail?date=${encodeURIComponent(selectedDate.value)}&code=${encodeURIComponent(item.stockCode)}`;
}

function scoreTone(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 'default';
  }
  if (numeric >= 15) {
    return 'success';
  }
  if (numeric <= -15) {
    return 'error';
  }
  return 'default';
}

function signalColor(signal?: string | null, score?: number | null) {
  if (signal?.includes('买')) {
    return 'green';
  }
  if (signal?.includes('卖') || signal?.includes('回避')) {
    return 'red';
  }
  return scoreTone(score) === 'success' ? 'green' : scoreTone(score) === 'error' ? 'red' : 'blue';
}

function applyUrl(date: string) {
  if (typeof window === 'undefined') {
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set('date', date);
  window.history.pushState({}, '', url);
}

async function loadAnalysis(date?: string, pushState = false) {
  loading.value = true;
  error.value = '';
  try {
    const payload = await fetchAnalysis(date);
    selectedDate.value = payload.tradeDate || '';
    summary.value = payload.summary;
    items.value = payload.items || [];
    if (pushState && selectedDate.value) {
      applyUrl(selectedDate.value);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  } finally {
    loading.value = false;
  }
}

async function loadInitial() {
  loading.value = true;
  error.value = '';
  try {
    const datePayload = await fetchDates();
    dates.value = datePayload.dates || [];
    const requestedDate = queryParam('date');
    await loadAnalysis(requestedDate || dates.value[0]?.tradeDate);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
    loading.value = false;
  }
}

function handleDateClick({ key }: { key: string }) {
  void loadAnalysis(key, true);
}

function handlePopState() {
  void loadAnalysis(queryParam('date'));
}

onMounted(() => {
  void loadInitial();
  window.addEventListener('popstate', handlePopState);
});

onBeforeUnmount(() => {
  window.removeEventListener('popstate', handlePopState);
});
</script>

<template>
  <div class="stock-shell stock-shell--wide">
    <aside class="stock-sidebar stock-sidebar--antd">
      <a-card size="small" :bordered="false" class="date-card">
        <template #title>交易日</template>
        <a-empty v-if="!dates.length && !loading" :image="null" description="暂无日期" />
        <a-menu
          v-else
          mode="inline"
          class="date-menu"
          :selected-keys="selectedDate ? [selectedDate] : []"
          @click="handleDateClick"
        >
          <a-menu-item v-for="date in dates" :key="date.tradeDate">
            <span class="date-menu__item">
              <span>{{ date.tradeDate }}</span>
              <a-tag>{{ date.stockCount }} 只</a-tag>
            </span>
          </a-menu-item>
        </a-menu>
      </a-card>
    </aside>

    <main class="stock-main stock-main--antd">
      <a-page-header class="dashboard-header" :title="selectedDate || '暂无分析数据'">
        <template #subTitle>
          <span>Daily Signal Snapshot</span>
        </template>
        <template #extra>
          <span v-if="summary?.updatedAt" class="stock-updated">更新 {{ summary.updatedAt }}</span>
        </template>
      </a-page-header>

      <a-alert v-if="error" type="error" show-icon :message="error" />
      <a-spin v-else-if="loading" class="dashboard-spin" tip="加载中..." />

      <template v-else>
        <a-row v-if="summary" :gutter="[12, 12]" class="summary-row">
          <a-col :xs="12" :sm="8" :md="4">
            <a-card size="small" :bordered="false">
              <a-statistic title="股票数" :value="summary.stockCount" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="8" :md="4">
            <a-card size="small" :bordered="false">
              <a-statistic title="平均分" :value="formatScore(summary.avgScore)" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="8" :md="5">
            <a-card size="small" :bordered="false">
              <a-statistic title="最高 / 最低" :value="`${formatScore(summary.maxScore)} / ${formatScore(summary.minScore)}`" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="12" :md="7">
            <a-card size="small" :bordered="false">
              <a-statistic
                title="买入 / 观望 / 卖出"
                :value="`${summary.buyBiasCount} / ${summary.watchCount} / ${summary.sellBiasCount}`"
              />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="12" :md="4">
            <a-card size="small" :bordered="false">
              <a-statistic title="数据提醒" :value="summary.sourceErrorCount" />
            </a-card>
          </a-col>
        </a-row>

        <a-card :bordered="false" class="analysis-card-antd">
          <template #title>
            <span class="table-title">
              <BarChartOutlined />
              当日分析列表
            </span>
          </template>
          <template #extra>
            <span class="table-extra">{{ tableRows.length }} 条记录</span>
          </template>

          <a-table
            size="middle"
            :columns="columns"
            :data-source="tableRows"
            :pagination="pagination"
            :scroll="{ x: 1280 }"
          >
            <template #emptyText>
              <a-empty description="暂无股票分析记录" />
            </template>

            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'stock'">
                <div class="stock-cell">
                  <a-typography-text strong>{{ record.stockCode }}</a-typography-text>
                  <a-typography-text type="secondary">{{ record.name || record.industry || '未命名' }}</a-typography-text>
                </div>
              </template>

              <template v-else-if="column.key === 'score'">
                <a-tag class="score-tag" :color="scoreTone(record.score)">
                  {{ formatScore(record.score) }}
                </a-tag>
              </template>

              <template v-else-if="column.key === 'signal'">
                <a-tag :color="signalColor(record.signalLabel, record.score)">
                  {{ record.signalLabel || '暂无' }}
                </a-tag>
              </template>

              <template v-else-if="column.key === 'shortTerm'">
                <div class="score-cell">
                  <a-tag :color="scoreTone(record.shortTermScore)">{{ formatScore(record.shortTermScore) }}</a-tag>
                  <span>{{ record.shortTermSignalLabel || '暂无' }}</span>
                </div>
              </template>

              <template v-else-if="column.key === 'mediumTerm'">
                <div class="score-cell">
                  <a-tag :color="scoreTone(record.mediumTermScore)">{{ formatScore(record.mediumTermScore) }}</a-tag>
                  <span>{{ record.mediumTermSignalLabel || '暂无' }}</span>
                </div>
              </template>

              <template v-else-if="column.key === 'longTerm'">
                <div class="score-cell">
                  <a-tag :color="scoreTone(record.longTermScore)">{{ formatScore(record.longTermScore) }}</a-tag>
                  <span>{{ record.longTermSignalLabel || '暂无' }}</span>
                </div>
              </template>

              <template v-else-if="column.key === 'conclusion'">
                <a-typography-text class="conclusion-cell" :ellipsis="{ tooltip: record.conclusion || '暂无结论' }">
                  {{ record.conclusion || '暂无结论' }}
                </a-typography-text>
              </template>

              <template v-else-if="column.key === 'quote'">
                <div class="number-stack">
                  <strong>{{ formatNumber(record.closePrice, 4) }}</strong>
                  <span>换手 {{ formatPercent(record.turnoverRate) }}</span>
                </div>
              </template>

              <template v-else-if="column.key === 'amount'">
                {{ formatCompact(record.amount) }}
              </template>

              <template v-else-if="column.key === 'trend'">
                <a-typography-text :ellipsis="{ tooltip: record.trendRating || record.regime || '暂无' }">
                  {{ record.trendRating || record.regime || '暂无' }}
                </a-typography-text>
              </template>

              <template v-else-if="column.key === 'dataStatus'">
                <a-tag :color="record.sourceErrorCount ? 'gold' : 'default'">
                  {{ record.sourceErrorCount ? `${record.sourceErrorCount} 条提醒` : '正常' }}
                </a-tag>
              </template>

              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" :href="detailHref(record)">
                  详情
                  <RightOutlined />
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </template>
    </main>
  </div>
</template>
