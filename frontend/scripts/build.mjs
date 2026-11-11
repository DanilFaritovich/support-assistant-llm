import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { build } from 'vite';

await build();
const serverDirectory = 'node_modules/.cache/support-assistant-ssg';
await build({
  build: { ssr: 'src/entry-server.ts', outDir: serverDirectory, emptyOutDir: true },
});
const { render, siteOrigin } = await import(
  pathToFileURL(resolve(serverDirectory, 'entry-server.js')).href
);
const shell = await readFile('dist/index.html', 'utf8');
const escape = (value) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

function document(html, language, metadata, prerendered = false) {
  const head = [
    `<meta name="description" content="${escape(metadata.description)}">`,
    `<link rel="canonical" href="${escape(metadata.canonical)}">`,
    ...metadata.alternates.map(
      ({ language, href }) =>
        `<link rel="alternate" hreflang="${language}" href="${escape(href)}">`,
    ),
  ].join('\n');
  return shell
    .replace(/<html lang="[^"]*">/, `<html lang="${language}">`)
    .replace(/<title>.*?<\/title>/, `<title>${escape(metadata.title)}</title>`)
    .replace('</head>', `${head}\n</head>`)
    .replace(
      '<div id="app"></div>',
      `<div id="app"${prerendered ? ' data-prerendered' : ''}>${html}</div>`,
    );
}

for (const locale of ['en', 'ru']) {
  const { html, metadata } = await render(locale);
  await mkdir(`dist/${locale}`, { recursive: true });
  await writeFile(`dist/${locale}/index.html`, document(html, locale, metadata, true));
}
const { metadata } = await render('en');
await writeFile(
  'dist/index.html',
  document(
    '<main><h1>Support Assistant</h1><p>Choose your language / Выберите язык</p><nav aria-label="Language / Язык"><a href="/en/" lang="en" hreflang="en">English</a> · <a href="/ru/" lang="ru" hreflang="ru">Русский</a></nav></main>',
    'en',
    {
      ...metadata,
      title: 'Support Assistant · English / Русский',
      canonical: `${siteOrigin}/`,
    },
  ),
);
await writeFile(
  'dist/sitemap.xml',
  `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${['en', 'ru'].map((locale) => `<url><loc>${escape(siteOrigin)}/${locale}/</loc>${metadata.alternates.map(({ language, href }) => `<xhtml:link rel="alternate" hreflang="${language}" href="${escape(href)}"/>`).join('')}</url>`).join('\n')}
</urlset>\n`,
);
await writeFile(
  'dist/robots.txt',
  `User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: ${siteOrigin}/sitemap.xml\n`,
);
console.log(`Prerendered /en/ and /ru/ for ${siteOrigin}`);
