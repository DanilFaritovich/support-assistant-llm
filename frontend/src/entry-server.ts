import { renderToString } from 'vue/server-renderer';
import { createMemoryHistory } from 'vue-router';

import { createApplication } from './app';
import { pageMetadata, siteOrigin } from './seo';
import type { Locale } from './messages';

export async function render(locale: Locale) {
  const { app, router } = createApplication(createMemoryHistory());
  await router.push(`/${locale}/`);
  await router.isReady();
  return { html: await renderToString(app), metadata: pageMetadata(locale) };
}

export { siteOrigin };
