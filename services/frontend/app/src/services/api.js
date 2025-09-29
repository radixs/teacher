import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api/v1'
});

export default {
  startSession(payload) {
    return client.post('/sessions', payload);
  },
  sendMessage(sessionId, payload) {
    return client.post(`/sessions/${sessionId}`, payload);
  },
  fetchSession(sessionId) {
    return client.get(`/sessions/${sessionId}`);
  }
};
