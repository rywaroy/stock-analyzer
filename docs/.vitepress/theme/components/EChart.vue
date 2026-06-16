<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    options: Record<string, unknown>;
    height?: string;
  }>(),
  {
    height: '320px',
  },
);

const chartEl = ref<HTMLDivElement | null>(null);
let chart: any = null;
let resizeObserver: ResizeObserver | null = null;

async function renderChart() {
  if (!chartEl.value || import.meta.env.SSR) {
    return;
  }
  const echarts = await import('echarts');
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }
  chart.setOption(props.options, true);
  chart.resize();
}

onMounted(async () => {
  await nextTick();
  await renderChart();
  if (chartEl.value && 'ResizeObserver' in window) {
    resizeObserver = new ResizeObserver(() => {
      chart?.resize();
    });
    resizeObserver.observe(chartEl.value);
  }
});

watch(
  () => props.options,
  async () => {
    await renderChart();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="chartEl" class="stock-chart" :style="{ height }" />
</template>
