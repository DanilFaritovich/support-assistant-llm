import { createApp, createSSRApp, defineComponent, h } from 'vue';
import { RouterView, type RouterHistory } from 'vue-router';

import { createSupportRouter } from './router';

export const Root = defineComponent({ render: () => h(RouterView) });

export function createApplication(history: RouterHistory, hydrate = true) {
  const app = (hydrate ? createSSRApp : createApp)(Root);
  const router = createSupportRouter(history);
  app.use(router);
  return { app, router };
}
