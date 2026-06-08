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
      <section class="flow-console" aria-live="polite">
        <div class="flow-console-header">
          <div>
            <h2>Live Flow Console</h2>
            <p>Recent runtime events pushed from the running containers.</p>
          </div>
          <span class="flow-status" :class="flowConnectionState">
            {{ flowStatusLabel }}
          </span>
        </div>
        <div class="flow-console-body" ref="flowLogEl">
          <p v-if="!flowEvents.length" class="flow-empty">
            No live events yet. Start a session or send a message to see the flow.
          </p>
          <article
            v-for="event in flowEvents"
            :key="event.id"
            class="flow-entry"
          >
            <header>
              <span class="service">{{ event.service }}</span>
              <span class="step">{{ event.step }}</span>
              <time :datetime="event.timestamp">{{ formatEventTime(event.timestamp) }}</time>
            </header>
            <p>{{ event.message }}</p>
            <pre v-if="hasContext(event.context)">{{ formatContext(event.context) }}</pre>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch, onBeforeUnmount, onMounted } from 'vue';
import { useStore } from 'vuex';
import ChatInput from '@/components/ChatInput.vue';
import ChatMessage from '@/components/ChatMessage.vue';
import { createFlowEventStream } from '@/services/api';

const store = useStore();
const hasSession = computed(() => store.getters.hasSession);
const sessionHistory = computed(() => store.getters.sessionHistory);
const goal = ref('');
const profile = ref('');
const historyEl = ref(null);
const flowLogEl = ref(null);
const flowEvents = ref([]);
const flowConnectionState = ref('connecting');
const chatPinnedToBottom = ref(true);
const flowPinnedToBottom = ref(true);
let flowEventSource = null;

const MAX_FLOW_EVENTS = 24;

const phaseLabel = computed(() => {
  const phase = store.state.phase ?? 'idle';
  return phase.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
});

const flowStatusLabel = computed(() => {
  if (flowConnectionState.value === 'open') {
    return 'Live';
  }

  if (flowConnectionState.value === 'error') {
    return 'Reconnecting';
  }

  return 'Connecting';
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
  try {
    await store.dispatch('sendMessage', { message });
  } catch (error) {
    // error state handled centrally by the store
  }
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
    minute: '2-digit',
    hour12: false
  }).format(date);
}

function scrollToBottom() {
  if (historyEl.value) {
    historyEl.value.scrollTop = historyEl.value.scrollHeight;
  }
}

function isNearBottom(element, threshold = 32) {
  if (!element) {
    return true;
  }

  return element.scrollHeight - element.scrollTop - element.clientHeight <= threshold;
}

function updateChatPinnedState() {
  chatPinnedToBottom.value = isNearBottom(historyEl.value);
}

function updateFlowPinnedState() {
  flowPinnedToBottom.value = isNearBottom(flowLogEl.value);
}

function scrollLogToBottom() {
  if (flowLogEl.value) {
    flowLogEl.value.scrollTop = flowLogEl.value.scrollHeight;
  }
}

function hasContext(context) {
  return Boolean(context && Object.keys(context).length);
}

function formatContext(context) {
  return JSON.stringify(context, null, 2);
}

function formatEventTime(timestamp) {
  if (!timestamp) {
    return '';
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(date);
}

function appendFlowEvent(event) {
  if (!event || !event.id) {
    return;
  }

  const shouldStayPinnedToBottom = isNearBottom(flowLogEl.value);

  const nextEvents = [...flowEvents.value, event];
  const deduped = nextEvents.filter(
    (entry, index, entries) => index === entries.findIndex((candidate) => candidate.id === entry.id)
  );

  flowEvents.value = deduped.slice(-1 * MAX_FLOW_EVENTS);
  flowPinnedToBottom.value = shouldStayPinnedToBottom;

  if (shouldStayPinnedToBottom) {
    nextTick(() => {
      scrollLogToBottom();
      flowPinnedToBottom.value = true;
    });
  }
}

function connectFlowStream() {
  if (typeof window === 'undefined' || flowEventSource) {
    return;
  }

  flowEventSource = createFlowEventStream();
  flowConnectionState.value = 'connecting';

  flowEventSource.addEventListener('open', () => {
    flowConnectionState.value = 'open';
  });

  flowEventSource.addEventListener('flow', (event) => {
    flowConnectionState.value = 'open';

    try {
      appendFlowEvent(JSON.parse(event.data));
    } catch (error) {
      flowConnectionState.value = 'error';
    }
  });

  flowEventSource.addEventListener('heartbeat', () => {
    flowConnectionState.value = 'open';
  });

  flowEventSource.onerror = () => {
    flowConnectionState.value = 'error';
  };
}

function disconnectFlowStream() {
  if (!flowEventSource) {
    return;
  }

  flowEventSource.close();
  flowEventSource = null;
}

watch(
  () => store.state.messages.length,
  async () => {
    await nextTick();
    if (chatPinnedToBottom.value) {
      scrollToBottom();
    }
  },
  { flush: 'post' }
);

watch(
  () => store.state.loading,
  async () => {
    await nextTick();
    if (chatPinnedToBottom.value) {
      scrollToBottom();
    }
  },
  { flush: 'post' }
);

watch(
  () => flowEvents.value.length,
  async () => {
    await nextTick();
    if (flowPinnedToBottom.value) {
      scrollLogToBottom();
    }
  },
  { flush: 'post' }
);

onMounted(() => {
  historyEl.value?.addEventListener('scroll', updateChatPinnedState, { passive: true });
  flowLogEl.value?.addEventListener('scroll', updateFlowPinnedState, { passive: true });
  connectFlowStream();
  scrollToBottom();
  scrollLogToBottom();
  updateChatPinnedState();
  updateFlowPinnedState();
});

onBeforeUnmount(() => {
  historyEl.value?.removeEventListener('scroll', updateChatPinnedState);
  flowLogEl.value?.removeEventListener('scroll', updateFlowPinnedState);
  disconnectFlowStream();
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
  box-sizing: border-box;
  resize: vertical;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(15, 23, 42, 0.6);
  color: inherit;
}

.new-session label {
  display: block;
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
  gap: 1rem;
  padding: 2rem;
}

.history {
  flex: 1;
  min-height: 0;
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

.flow-console {
  min-height: 240px;
  max-height: 320px;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.55);
  overflow: hidden;
}

.flow-console-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  background: rgba(15, 23, 42, 0.72);
}

.flow-console-header h2 {
  margin: 0;
  font-size: 1rem;
}

.flow-console-header p {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  opacity: 0.75;
}

.flow-status {
  flex-shrink: 0;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.flow-status.connecting {
  background: rgba(59, 130, 246, 0.2);
  color: #bfdbfe;
}

.flow-status.open {
  background: rgba(16, 185, 129, 0.2);
  color: #a7f3d0;
}

.flow-status.error {
  background: rgba(248, 113, 113, 0.2);
  color: #fecaca;
}

.flow-console-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.9rem 1.1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  font-family: "IBM Plex Mono", "Fira Code", monospace;
}

.flow-empty {
  margin: auto 0;
  font-size: 0.9rem;
  opacity: 0.7;
}

.flow-entry {
  padding: 0.8rem 0.9rem;
  border-radius: 0.85rem;
  background: rgba(2, 6, 23, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.flow-entry header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.5rem;
  font-size: 0.78rem;
}

.flow-entry .service {
  color: #7dd3fc;
  font-weight: 700;
}

.flow-entry .step {
  color: #c4b5fd;
}

.flow-entry time {
  margin-left: auto;
  opacity: 0.65;
}

.flow-entry p {
  margin: 0;
  line-height: 1.45;
  font-size: 0.9rem;
}

.flow-entry pre {
  margin: 0.65rem 0 0;
  padding: 0.65rem 0.75rem;
  border-radius: 0.65rem;
  overflow-x: auto;
  background: rgba(15, 23, 42, 0.8);
  color: #cbd5e1;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  }

  .conversation {
    padding: 1rem;
  }

  .flow-console {
    max-height: 360px;
  }
}
</style>
