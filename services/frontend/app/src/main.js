import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import store from './store';

import './styles.css';

const app = createApp(App);
app.use(store);
app.use(router);

store.dispatch('hydrateFromStorage').finally(() => {
  app.mount('#app');
});
