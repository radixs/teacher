<template>
  <div :class="wrapperClass">
    <div class="meta">
      <span class="role">{{ roleLabel }}</span>
      <span class="timestamp">{{ formattedTimestamp }}</span>
    </div>
    <p class="content">{{ message.content }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
});

const wrapperClass = computed(() => [
  'chat-message',
  props.message.role === 'assistant' ? 'assistant' : 'user'
]);

const roleLabel = computed(() => props.message.role === 'assistant' ? 'Assistant' : 'You');

const formattedTimestamp = computed(() => {
  const raw = props.message.created_at ?? props.message.timestamp;
  if (!raw) {
    return '';
  }
  try {
    return new Date(raw).toLocaleTimeString();
  } catch (error) {
    return raw;
  }
});
</script>

<style scoped>
.chat-message {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  max-width: 80%;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.chat-message.user {
  margin-left: auto;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #fff;
}

.chat-message.assistant {
  margin-right: auto;
  background: rgba(15, 23, 42, 0.6);
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  opacity: 0.75;
}

.content {
  margin: 0;
  white-space: pre-wrap;
}
</style>
