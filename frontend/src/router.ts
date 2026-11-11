import { createRouter, type RouterHistory } from 'vue-router';

import App from './App.vue';
import { getInitialLocale } from './locale';

export function createSupportRouter(history: RouterHistory) {
  return createRouter({
    history,
    routes: [
      { path: '/', redirect: () => `/${getInitialLocale()}/` },
      { path: '/en/', component: App, meta: { locale: 'en' } },
      { path: '/ru/', component: App, meta: { locale: 'ru' } },
    ],
  });
}
