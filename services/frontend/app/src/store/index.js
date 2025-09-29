import { createStore } from 'vuex';
import api from '@/services/api';

const store = createStore({
  state: () => ({
    sessionId: null,
    goal: '',
    messages: [],
    loading: false,
    error: null,
    phase: 'idle'
  }),
  getters: {
    hasSession: (state) => Boolean(state.sessionId)
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
    }
  },
  actions: {
    async startSession({ commit }, { goal, profile }) {
      commit('setLoading', true);
      commit('setError', null);
      try {
        const { data } = await api.startSession({ goal, profile });
        commit('setGoal', goal);
        commit('setSession', data);
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
        return data;
      } catch (error) {
        commit('setError', error?.message ?? 'Failed to send message');
        throw error;
      } finally {
        commit('setLoading', false);
      }
    },
    async fetchSession({ commit }, sessionId) {
      commit('setLoading', true);
      commit('setError', null);
      try {
        const { data } = await api.fetchSession(sessionId);
        commit('setSession', data);
        return data;
      } catch (error) {
        commit('setError', error?.message ?? 'Failed to load session');
        throw error;
      } finally {
        commit('setLoading', false);
      }
    }
  }
});

export default store;
