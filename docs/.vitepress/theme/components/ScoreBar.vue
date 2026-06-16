<script setup lang="ts">
import { computed } from 'vue';
import { formatScore, scoreWidth, signalTone } from '../formatters';

const props = defineProps<{
  label: string;
  score?: number | null;
  signal?: string | null;
}>();

const tone = computed(() => signalTone(props.signal, props.score));
const width = computed(() => scoreWidth(props.score));
</script>

<template>
  <div class="score-bar">
    <div class="score-bar__meta">
      <span>{{ label }}</span>
      <strong>{{ formatScore(score) }}</strong>
    </div>
    <div class="score-bar__track">
      <span class="score-bar__fill" :class="`score-bar__fill--${tone}`" :style="{ width }" />
    </div>
    <div v-if="signal" class="score-bar__signal">{{ signal }}</div>
  </div>
</template>
