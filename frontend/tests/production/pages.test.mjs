import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { JSDOM } from 'jsdom';

const read = (path) => readFile(`dist/${path}`, 'utf8');
const root = new JSDOM(await read('index.html')).window.document;
const origin = new URL(root.querySelector('link[rel="canonical"]').href).origin;

for (const [locale, heading, example] of [
  ['en', 'IT ticket processing', 'Sign-in problem'],
  ['ru', 'Обработка IT-заявок', 'Проблема со входом'],
]) {
  test(`${locale} has crawlable content and reciprocal metadata before JavaScript`, async () => {
    const document = new JSDOM(await read(`${locale}/index.html`)).window.document;
    assert.equal(document.documentElement.lang, locale);
    assert.equal(document.querySelector('h1').textContent, heading);
    assert.ok(document.querySelector('#about-title'));
    assert.ok(document.querySelector('#demo-ticket').textContent.includes(example));
    assert.equal(
      document.querySelector('link[rel="canonical"]').href,
      `${origin}/${locale}/`,
    );
    assert.ok(document.querySelector('meta[name="description"]').content.length > 50);
    for (const language of ['en', 'ru', 'x-default']) {
      const expected = `${origin}/${language === 'x-default' ? '' : `${language}/`}`;
      assert.equal(
        document.querySelector(`link[hreflang="${language}"]`).href,
        expected,
      );
    }
    assert.equal(document.querySelector('a[lang="en"]').getAttribute('href'), '/en/');
    assert.equal(document.querySelector('a[lang="ru"]').getAttribute('href'), '/ru/');
    assert.ok(document.querySelector('script[type="module"][src^="/assets/"]'));
    assert.ok(document.querySelector('#app[data-prerendered]'));
    assert.equal(document.querySelector('#ticket-text').value, '');
  });
}

test('sitemap and robots agree with canonical URLs', async () => {
  const xml = new JSDOM(await read('sitemap.xml'), { contentType: 'application/xml' })
    .window.document;
  assert.deepEqual(
    [...xml.querySelectorAll('loc')].map((node) => node.textContent),
    [`${origin}/en/`, `${origin}/ru/`],
  );
  assert.equal(xml.getElementsByTagName('xhtml:link').length, 6);
  assert.ok((await read('robots.txt')).includes(`Sitemap: ${origin}/sitemap.xml`));
  assert.equal(root.querySelector('a[lang="ru"]').getAttribute('href'), '/ru/');
});
