<template>
  <div class="chat-layout">
    <aside class="sidebar">
      <h1>Teacher</h1>
      <p class="sub">Personalized learning companion.</p>

      <section class="session-info" v-if="hasSession">
        <h2>Active Goal</h2>
        <p>{{ store.state.goal }}</p>
        <p class="phase">Phase: {{ phaseLabel }}</p>
      </section>

      <section class="session-list" v-if="sessionHistory.length">
        <h2>Sessions</h2>
        <ul>
          <li v-for="session in sessionHistory" :key="session.id">
            <button
              type="button"
              class="session-entry"
              :class="{ active: session.id === store.state.sessionId }"
              :disabled="store.state.loading && session.id === store.state.sessionId"
              @click="resume(session.id)"
            >
              <span class="title">{{ session.goal || 'Untitled Goal' }}</span>
              <span class="meta">
                {{ formatPhase(session.phase) }}
                <template v-if="session.updated_at"> · {{ formatUpdated(session.updated_at) }}</template>
              </span>
            </button>
          </li>
        </ul>
      </section>

      <section class="new-session">
        <h2>Start New Session</h2>
        <label>
          Learning goal
          <textarea
            v-model="goal"
            rows="3"
            placeholder="e.g. Become an ESRE engineer"
          ></textarea>
        </label>
        <label>
          Background (optional)
          <textarea
            v-model="profile"
            rows="4"
            placeholder="Summarize your experience"
          ></textarea>
        </label>
        <button :disabled="store.state.loading || !goal.trim()" @click="start">
          Start Session
        </button>
        <p v-if="store.state.error && !hasSession" class="error">{{ store.state.error }}</p>
      </section>
    </aside>

    <main class="conversation">
      <div class="history" ref="historyEl">
        <ChatMessage
          v-for="(message, index) in store.state.messages"
          :key="index"
          :message="message"
        />
        <div v-if="store.state.loading" class="typing-indicator">
          Assistant is thinking…
        </div>
      </div>
      <footer class="composer" v-if="hasSession">
        <ChatInput
          :loading="store.state.loading"
          :error="store.state.error"
          @submit="send"
        />
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue';
import { useStore } from 'vuex';
import ChatInput from '@/components/ChatInput.vue';
import ChatMessage from '@/components/ChatMessage.vue';

const store = useStore();
const hasSession = computed(() => store.getters.hasSession);
const sessionHistory = computed(() => store.getters.sessionHistory);
const goal = ref('');
const profile = ref('');
const historyEl = ref(null);

const phaseLabel = computed(() => {
  const phase = store.state.phase ?? 'idle';
  return phase.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
});

async function start() {
  if (!goal.value.trim()) {
    return;
  }

  try {
    await store.dispatch('startSession', {
      goal: goal.value.trim(),
      profile: profile.value ? { summary: profile.value.trim() } : undefined
    });
    goal.value = '';
    profile.value = '';
  } catch (error) {
    // keep form values so the learner can adjust and retry
  }
}

async function send(message) {
  await store.dispatch('sendMessage', { message });
}

async function resume(sessionId) {
  if (!sessionId || sessionId === store.state.sessionId) {
    return;
  }

  try {
    await store.dispatch('loadSession', sessionId);
  } catch (error) {
    // error state handled centrally by the store
  }
}

function formatPhase(phase) {
  const value = phase ?? 'idle';
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatUpdated(timestamp) {
  if (!timestamp) {
    return '';
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function scrollToBottom() {
  if (historyEl.value) {
    historyEl.value.scrollTop = historyEl.value.scrollHeight;
  }
}

watch(
  () => store.state.messages.length,
  () => scrollToBottom()
);

onMounted(() => {
  scrollToBottom();
});
</script>

<style scoped>
.chat-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  min-height: 100vh;
  background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.25), transparent),
    radial-gradient(circle at bottom right, rgba(236, 72, 153, 0.2), transparent);
}

.sidebar {
  padding: 2rem 1.5rem;
  background: rgba(15, 23, 42, 0.85);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border-right: 1px solid rgba(148, 163, 184, 0.2);
}

.sidebar h1 {
  margin: 0;
}

.sub {
  margin: 0;
  opacity: 0.8;
}

.session-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.session-entry {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  padding: 0.75rem 0.85rem;
  border-radius: 0.75rem;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.6);
  color: inherit;
  text-align: left;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.session-entry .title {
  font-weight: 600;
}

.session-entry .meta {
  font-size: 0.8rem;
  opacity: 0.7;
}

.session-entry:not(.active):hover {
  border-color: rgba(148, 163, 184, 0.6);
  background: rgba(15, 23, 42, 0.75);
}

.session-entry.active {
  border-color: rgba(129, 140, 248, 0.9);
  background: rgba(79, 70, 229, 0.25);
}

textarea {
  margin-top: 0.5rem;
  width: 100%;
  resize: vertical;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(15, 23, 42, 0.6);
  color: inherit;
}

button {
  align-self: flex-start;
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  border: none;
  font-weight: 600;
  color: #0f172a;
  background: linear-gradient(135deg, #38bdf8, #818cf8);
}

button:disabled {
  opacity: 0.6;
}

.error {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #fca5a5;
}

.conversation {
  display: flex;
  flex-direction: column;
  padding: 2rem;
}

.history {
  flex: 1;
  overflow-y: auto;
  padding-right: 1rem;
  display: flex;
  flex-direction: column;
}

.typing-indicator {
  align-self: flex-start;
  font-size: 0.85rem;
  opacity: 0.7;
}

.composer {
  padding-top: 1rem;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  }
}
</style>
