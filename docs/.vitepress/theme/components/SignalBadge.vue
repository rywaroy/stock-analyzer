<script setup lang="ts">
import { computed } from 'vue';
import { signalTone } from '../formatters';

const props = defineProps<{
  signal?: string | null;
  score?: number | null;
}>();

const tone = computed(() => signalTone(props.signal, props.score));
</script>

<template>
  <span class="signal-badge" :class="`signal-badge--${tone}`">{{ signal || '暂无' }}</span>
</template>
