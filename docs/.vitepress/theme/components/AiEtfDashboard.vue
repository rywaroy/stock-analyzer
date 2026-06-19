<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { FundProjectionScreenOutlined, RightOutlined } from '@ant-design/icons-vue';
import { fetchAiEtf, fetchAiEtfDates } from '../api';
import { formatNumber, formatPercent, formatScore, queryParam } from '../formatters';

type EtfDate = {
  tradeDate: string;
  holdingCount: number;
  turnoverPct: number | null;
  totalPnl: number | null;
  updatedAt: string;
};

const dates = ref<EtfDate[]>([]);
const selectedDate = ref('');
const payload = ref<any | null>(null);
const loading = ref(true);
const error = ref('');

const snapshot = computed(() => payload.value?.snapshot || null);
const holdings = computed(() =>
  (payload.value?.holdings || [])
    .filter((item: any) => Number(item.targetWeightPct) > 0)
    .map((item: any) => ({ ...item, key: `${item.stockCode}-${item.action}` })),
);
const rebalance = computed(() =>
  (payload.value?.rebalance || []).map((item: any) => ({
    ...item,
    key: `${item.stockCode}-${item.action}`,
  })),
);

const holdingColumns = [
  { title: '股票', key: 'stock', width: 180, fixed: 'left' },
  { title: '动作', key: 'action', width: 96 },
  { title: '原权重', key: 'previousWeightPct', width: 96 },
  { title: '新权重', key: 'targetWeightPct', width: 96 },
  { title: '变化', key: 'weightDeltaPct', width: 96 },
  { title: '参考价', key: 'referencePrice', width: 112 },
  { title: '总分', key: 'score', width: 82 },
  { title: '短/中/长', key: 'horizon', width: 140 },
  { title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 86 },
  { title: '理由', dataIndex: 'rationale', key: 'rationale', ellipsis: true },
  { title: '', key: 'detail', width: 88, fixed: 'right' },
];

const rebalanceColumns = [
  { title: '股票', key: 'stock', width: 180 },
  { title: '动作', key: 'action', width: 96 },
  { title: '权重变化', key: 'weightDeltaPct', width: 120 },
  { title: '参考价', key: 'referencePrice', width: 112 },
  { title: '模拟金额变化', key: 'simulatedNotionalDelta', width: 140 },
  { title: '已实现盈亏', key: 'realizedPnl', width: 128 },
  { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true },
];

function actionLabel(action?: string) {
  const labels: Record<string, string> = {
    buy: '买入',
    sell: '卖出',
    increase: '加仓',
    reduce: '减仓',
    hold: '保留',
    watch: '观察',
  };
  return labels[action || ''] || action || '暂无';
}

function actionColor(action?: string) {
  const colors: Record<string, string> = {
    buy: 'green',
    increase: 'cyan',
    sell: 'red',
    reduce: 'orange',
    hold: 'blue',
    watch: 'default',
  };
  return colors[action || ''] || 'default';
}

function signedPercent(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${formatPercent(numeric)}`;
}

function signedNumber(value: unknown, digits = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '暂无';
  }
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${formatNumber(numeric, digits)}`;
}

function detailHref(item: any) {
  const date = snapshot.value?.tradeDate || selectedDate.value;
  return `/analysis/detail?date=${encodeURIComponent(date)}&code=${encodeURIComponent(item.stockCode)}`;
}

function applyUrl(date: string) {
  if (typeof window === 'undefined') {
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set('date', date);
  window.history.pushState({}, '', url);
}

async function loadPortfolio(date?: string, pushState = false) {
  loading.value = true;
  error.value = '';
  try {
    const result = await fetchAiEtf(date);
    payload.value = result;
    selectedDate.value = result.snapshot?.tradeDate || date || '';
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
    const datePayload = await fetchAiEtfDates();
    dates.value = datePayload.dates || [];
    const requestedDate = queryParam('date');
    await loadPortfolio(requestedDate || dates.value[0]?.tradeDate);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
    loading.value = false;
  }
}

function handleDateClick({ key }: { key: string }) {
  void loadPortfolio(key, true);
}

function handlePopState() {
  void loadPortfolio(queryParam('date'));
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
        <template #title>组合日期</template>
        <a-empty v-if="!dates.length && !loading" :image="null" description="暂无组合" />
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
              <a-tag>{{ date.holdingCount }} 只</a-tag>
            </span>
          </a-menu-item>
        </a-menu>
      </a-card>
    </aside>

    <main class="stock-main stock-main--antd">
      <a-page-header class="dashboard-header" :title="selectedDate || '暂无 AI 推荐 ETF'">
        <template #subTitle>
          <span>AI Recommended ETF</span>
        </template>
        <template #extra>
          <span v-if="snapshot?.updatedAt" class="stock-updated">更新 {{ snapshot.updatedAt }}</span>
        </template>
      </a-page-header>

      <a-alert v-if="error" type="error" show-icon :message="error" />
      <a-spin v-else-if="loading" class="dashboard-spin" tip="加载中..." />
      <a-empty v-else-if="!snapshot" description="暂无 AI 推荐 ETF 组合" />

      <template v-else>
        <a-alert class="etf-rule" type="info" show-icon :message="snapshot.selectionRule || '暂无选股规则'" />

        <a-row :gutter="[12, 12]" class="summary-row">
          <a-col :xs="12" :sm="8" :md="4">
            <a-card size="small" :bordered="false">
              <a-statistic title="持仓数" :value="snapshot.holdingCount" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="8" :md="5">
            <a-card size="small" :bordered="false">
              <a-statistic title="模拟 NAV" :value="formatNumber(snapshot.nav, 2)" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="8" :md="5">
            <a-card size="small" :bordered="false">
              <a-statistic title="累计收益" :value="formatPercent(snapshot.cumulativeReturnPct)" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="12" :md="5">
            <a-card size="small" :bordered="false">
              <a-statistic title="总盈亏" :value="signedNumber(snapshot.totalPnl, 2)" />
            </a-card>
          </a-col>
          <a-col :xs="12" :sm="12" :md="5">
            <a-card size="small" :bordered="false">
              <a-statistic title="本次换手" :value="formatPercent(snapshot.turnoverPct)" />
            </a-card>
          </a-col>
        </a-row>

        <a-card :bordered="false" class="analysis-card-antd">
          <template #title>
            <span class="table-title">
              <FundProjectionScreenOutlined />
              当前持仓
            </span>
          </template>
          <template #extra>
            <span class="table-extra">{{ holdings.length }} 只</span>
          </template>

          <a-table
            size="middle"
            :columns="holdingColumns"
            :data-source="holdings"
            :pagination="false"
            :scroll="{ x: 1280 }"
          >
            <template #emptyText>
              <a-empty description="暂无持仓" />
            </template>

            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'stock'">
                <div class="stock-cell">
                  <a-typography-text strong>{{ record.stockCode }}</a-typography-text>
                  <a-typography-text type="secondary">{{ record.stockName || record.industry || '未命名' }}</a-typography-text>
                </div>
              </template>

              <template v-else-if="column.key === 'action'">
                <a-tag :color="actionColor(record.action)">{{ actionLabel(record.action) }}</a-tag>
              </template>

              <template v-else-if="column.key === 'previousWeightPct'">
                {{ formatPercent(record.previousWeightPct) }}
              </template>

              <template v-else-if="column.key === 'targetWeightPct'">
                <strong>{{ formatPercent(record.targetWeightPct) }}</strong>
              </template>

              <template v-else-if="column.key === 'weightDeltaPct'">
                <span :class="Number(record.weightDeltaPct) >= 0 ? 'score-value--positive' : 'score-value--negative'">
                  {{ signedPercent(record.weightDeltaPct) }}
                </span>
              </template>

              <template v-else-if="column.key === 'referencePrice'">
                {{ formatNumber(record.referencePrice, 4) }}
              </template>

              <template v-else-if="column.key === 'score'">
                <a-tag class="score-tag">{{ formatScore(record.score) }}</a-tag>
              </template>

              <template v-else-if="column.key === 'horizon'">
                <div class="number-stack">
                  <strong>{{ formatScore(record.shortTermScore) }} / {{ formatScore(record.mediumTermScore) }} / {{ formatScore(record.longTermScore) }}</strong>
                  <span>短 / 中 / 长</span>
                </div>
              </template>

              <template v-else-if="column.key === 'detail'">
                <a-button type="link" size="small" :href="detailHref(record)">
                  详情
                  <RightOutlined />
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>

        <a-card :bordered="false" class="analysis-card-antd">
          <template #title>调仓动作</template>
          <template #extra>
            <span class="table-extra">{{ rebalance.length }} 条</span>
          </template>
          <a-table
            size="middle"
            :columns="rebalanceColumns"
            :data-source="rebalance"
            :pagination="false"
            :scroll="{ x: 980 }"
          >
            <template #emptyText>
              <a-empty description="暂无调仓记录" />
            </template>

            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'stock'">
                <div class="stock-cell">
                  <a-typography-text strong>{{ record.stockCode }}</a-typography-text>
                  <a-typography-text type="secondary">{{ record.stockName || '未命名' }}</a-typography-text>
                </div>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-tag :color="actionColor(record.action)">{{ actionLabel(record.action) }}</a-tag>
              </template>
              <template v-else-if="column.key === 'weightDeltaPct'">
                {{ formatPercent(record.previousWeightPct) }} → {{ formatPercent(record.targetWeightPct) }}
                <small class="etf-delta">{{ signedPercent(record.weightDeltaPct) }}</small>
              </template>
              <template v-else-if="column.key === 'referencePrice'">
                {{ formatNumber(record.referencePrice, 4) }}
              </template>
              <template v-else-if="column.key === 'simulatedNotionalDelta'">
                {{ signedNumber(record.simulatedNotionalDelta, 2) }}
              </template>
              <template v-else-if="column.key === 'realizedPnl'">
                {{ signedNumber(record.realizedPnl, 2) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </template>
    </main>
  </div>
</template>
