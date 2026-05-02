import { createStore } from 'vuex';
import api from '@/services/api';

const HISTORY_STORAGE_KEY = 'teacher.sessionHistory';
const ACTIVE_SESSION_KEY = 'teacher.activeSessionId';
const isBrowser = typeof window !== 'undefined';

const safeParseJson = (value, fallback) => {
  if (!value) {
    return fallback;
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
};

const loadPersistedHistory = () => {
  if (!isBrowser) {
    return [];
  }
  return safeParseJson(window.localStorage.getItem(HISTORY_STORAGE_KEY), []);
};

const persistHistory = (history) => {
  if (!isBrowser) {
    return;
  }
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
};

const loadActiveSessionId = () => {
  if (!isBrowser) {
    return null;
  }
  return window.localStorage.getItem(ACTIVE_SESSION_KEY);
};

const persistActiveSessionId = (sessionId) => {
  if (!isBrowser) {
    return;
  }
  if (sessionId) {
    window.localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  } else {
    window.localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
};

const toSummary = (session) => ({
  id: session.id,
  goal: session.goal,
  phase: session.phase,
  updated_at: session.updated_at,
  created_at: session.created_at
});

const initialHistory = loadPersistedHistory();
const initialActiveSessionId = loadActiveSessionId();

const store = createStore({
  state: () => ({
    sessionId: null,
    goal: '',
    messages: [],
    loading: false,
    error: null,
    phase: 'idle',
    sessionHistory: initialHistory,
    pendingRestoreId: initialActiveSessionId
  }),
  getters: {
    hasSession: (state) => Boolean(state.sessionId),
    sessionHistory: (state) => state.sessionHistory
  },
  mutations: {
    setLoading(state, value) {
      state.loading = value;
    },
    setError(state, message) {
      state.error = message;
    },
    setSession(state, payload) {
      state.sessionId = payload?.id ?? null;
      state.messages = payload?.messages ?? [];
      state.phase = payload?.phase ?? 'idle';
    },
    appendMessage(state, message) {
      state.messages.push(message);
    },
    setGoal(state, goal) {
      state.goal = goal;
    },
    setSessionHistory(state, history) {
      state.sessionHistory = history;
    },
    upsertSessionSummary(state, summary) {
      if (!summary?.id) {
        return;
      }

      const existingIndex = state.sessionHistory.findIndex((item) => item.id === summary.id);
      const merged = existingIndex >= 0
        ? { ...state.sessionHistory[existingIndex], ...summary }
        : summary;

      if (existingIndex >= 0) {
        state.sessionHistory.splice(existingIndex, 1);
      }

      state.sessionHistory = [merged, ...state.sessionHistory];
      persistHistory(state.sessionHistory);
    },
    removeSessionSummary(state, sessionId) {
      state.sessionHistory = state.sessionHistory.filter((item) => item.id !== sessionId);
      persistHistory(state.sessionHistory);
    },
    clearPendingRestore(state) {
      state.pendingRestoreId = null;
    }
  },
  actions: {
    async hydrateFromStorage({ state, commit, dispatch }) {
      const history = loadPersistedHistory();
      commit('setSessionHistory', history);

      if (state.pendingRestoreId) {
        try {
          await dispatch('loadSession', state.pendingRestoreId);
        } catch (error) {
          commit('removeSessionSummary', state.pendingRestoreId);
          persistActiveSessionId(null);
        } finally {
          commit('clearPendingRestore');
        }
      }
    },
    async startSession({ commit }, { goal, profile }) {
      commit('setLoading', true);
      commit('setError', null);
      try {
        const { data } = await api.startSession({ goal, profile });
        commit('setGoal', goal);
        commit('setSession', data);
        commit('upsertSessionSummary', toSummary(data));
        persistActiveSessionId(data.id);
        return data;
      } catch (error) {
        commit('setError', error?.message ?? 'Failed to start session');
        throw error;
      } finally {
        commit('setLoading', false);
      }
    },
    async sendMessage({ state, commit }, { message, metadata }) {
      if (!state.sessionId) {
        throw new Error('Session has not been started');
      }

      commit('setLoading', true);
      commit('setError', null);
      try {
        commit('appendMessage', {
          role: 'user',
          content: message,
          created_at: new Date().toISOString()
        });

        const { data } = await api.sendMessage(state.sessionId, { message, metadata });
        commit('appendMessage', data.last_message);
        commit('setSession', data.session);
        commit('upsertSessionSummary', toSummary(data.session));
        persistActiveSessionId(data.session.id);
        return data;
      } catch (error) {
        commit('setError', error?.message ?? 'Failed to send message');
        throw error;
      } finally {
        commit('setLoading', false);
      }
    },
    async loadSession({ commit }, sessionId) {
      commit('setLoading', true);
      commit('setError', null);
      try {
        const { data } = await api.fetchSession(sessionId);
        commit('setGoal', data.goal);
        commit('setSession', data);
        commit('upsertSessionSummary', toSummary(data));
        persistActiveSessionId(data.id);
        return data;
      } catch (error) {
        if (error?.response?.status === 404) {
          commit('removeSessionSummary', sessionId);
          persistActiveSessionId(null);
        }
        commit('setError', error?.message ?? 'Failed to load session');
        throw error;
      } finally {
        commit('setLoading', false);
      }
    }
  }
});

export default store;
