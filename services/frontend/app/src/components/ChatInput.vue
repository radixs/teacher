<template>
  <form class="chat-input" @submit.prevent="onSubmit">
    <textarea
      v-model="draft"
      rows="3"
      placeholder="Type your response or use commands like /no more"
    ></textarea>
    <div class="actions">
      <span v-if="error" class="error">{{ error }}</span>
      <button type="submit" :disabled="disabled">
        {{ disabled ? 'Sending…' : 'Send' }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const emit = defineEmits(['submit']);

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
});

const draft = ref('');

const disabled = computed(() => props.loading || draft.value.trim() === '');

function onSubmit() {
  if (disabled.value) {
    return;
  }
  emit('submit', draft.value.trim());
  draft.value = '';
}

watch(
  () => props.loading,
  (loading) => {
    if (!loading) {
      draft.value = draft.value.trim();
    }
  }
);
</script>

<style scoped>
.chat-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

textarea {
  resize: vertical;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(15, 23, 42, 0.85);
  color: inherit;
}

textarea:focus {
  outline: 2px solid rgba(59, 130, 246, 0.75);
}

.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error {
  color: #f87171;
  font-size: 0.85rem;
}

button {
  background: linear-gradient(135deg, #22c55e, #14b8a6);
  border: none;
  border-radius: 999px;
  color: #0f172a;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  transition: transform 0.15s ease;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}
</style>
