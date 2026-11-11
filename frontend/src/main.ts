import { createWebHistory } from 'vue-router';

import { createApplication } from './app';
import './style.css';

const container = document.querySelector('#app');
const { app, router } = createApplication(
  createWebHistory(),
  container?.hasAttribute('data-prerendered'),
);
await router.isReady();
app.mount('#app');
