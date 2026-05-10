import axios from 'axios';

const FALLBACK_BASE_URL = 'http://localhost:8080/api/v1';

const resolveBrowserFallback = () => {
  if (typeof window === 'undefined') {
    return FALLBACK_BASE_URL;
  }

  const { protocol, hostname } = window.location;
  const defaultPort = protocol === 'https:' ? '' : '8080';
  const portSegment = defaultPort ? `:${defaultPort}` : '';
  return `${protocol}//${hostname}${portSegment}/api/v1`;
};

const resolveBaseUrl = () => {
  const configured = import.meta.env.VITE_API_BASE_URL;

  if (!configured) {
    return resolveBrowserFallback();
  }

  if (typeof window !== 'undefined') {
    try {
      const parsed = new URL(configured);
      const isServiceHostname =
        !parsed.hostname.includes('.') && !['localhost', '127.0.0.1'].includes(parsed.hostname);

      if (isServiceHostname) {
        const { protocol, hostname } = window.location;
        const inferredPort = parsed.port || (protocol === 'https:' ? '' : '8080');
        const portSegment = inferredPort ? `:${inferredPort}` : '';
        const pathname = parsed.pathname === '/' ? '' : parsed.pathname;
        return `${protocol}//${hostname}${portSegment}${pathname}` || resolveBrowserFallback();
      }
    } catch (error) {
      // Ignore URL parsing errors and fall back to the configured value below.
    }
  }

  return configured;
};

const client = axios.create({
  baseURL: resolveBaseUrl()
});

export const getApiBaseUrl = () => client.defaults.baseURL;

export const createFlowEventStream = () => new EventSource(`${getApiBaseUrl()}/flow-events/stream`);

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
