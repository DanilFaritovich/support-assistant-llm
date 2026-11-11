import { messages, type Locale } from './messages';

export function resolveSiteOrigin(value: string): string {
  const url = new URL(value);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== '/' ||
    (url.protocol !== 'https:' && !(local && url.protocol === 'http:'))
  ) {
    throw new Error(
      'VITE_SITE_ORIGIN must be an HTTPS origin without a path, query or credentials (HTTP is allowed for localhost).',
    );
  }
  return url.origin;
}

export const siteOrigin = resolveSiteOrigin(
  import.meta.env.VITE_SITE_ORIGIN || 'https://support.danil-miftakhov.dev',
);

export function pageMetadata(locale: Locale) {
  return {
    title: `${messages[locale].title} · Support Assistant`,
    description: messages[locale].seoDescription,
    canonical: `${siteOrigin}/${locale}/`,
    alternates: [
      { language: 'en', href: `${siteOrigin}/en/` },
      { language: 'ru', href: `${siteOrigin}/ru/` },
      { language: 'x-default', href: `${siteOrigin}/` },
    ],
  };
}

export function updatePageMetadata(locale: Locale): void {
  const metadata = pageMetadata(locale);
  document.documentElement.lang = locale;
  document.title = metadata.title;
  let description = document.head.querySelector<HTMLMetaElement>(
    'meta[name="description"]',
  );
  if (!description) {
    description = document.createElement('meta');
    description.name = 'description';
    document.head.append(description);
  }
  description.content = metadata.description;
  let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement('link');
    canonical.rel = 'canonical';
    document.head.append(canonical);
  }
  canonical.href = metadata.canonical;
  document.head
    .querySelectorAll('link[rel="alternate"][hreflang]')
    .forEach((link) => link.remove());
  for (const alternate of metadata.alternates) {
    const link = document.createElement('link');
    link.rel = 'alternate';
    link.hreflang = alternate.language;
    link.href = alternate.href;
    document.head.append(link);
  }
}
