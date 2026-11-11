import { describe, expect, it } from 'vitest';

import { pageMetadata, resolveSiteOrigin } from '../seo';

describe('SEO metadata', () => {
  it('uses each page as its own canonical and includes both languages', () => {
    expect(pageMetadata('en').canonical).toBe(
      'https://support.danil-miftakhov.dev/en/',
    );
    expect(pageMetadata('ru').canonical).toBe(
      'https://support.danil-miftakhov.dev/ru/',
    );
    expect(pageMetadata('en').alternates).toEqual(pageMetadata('ru').alternates);
    expect(pageMetadata('en').description).not.toBe(pageMetadata('ru').description);
  });
  it.each([
    'https://example.com/path',
    'https://user:password@example.com',
    'http://example.com',
    'https://example.com/?q=x',
    'https://example.com/#x',
    'not a URL',
  ])('rejects invalid public origins: %s', (value) => {
    expect(() => resolveSiteOrigin(value)).toThrow();
  });
  it('accepts local preview origins and normalizes trailing slashes', () => {
    expect(resolveSiteOrigin('http://localhost:8080/')).toBe('http://localhost:8080');
  });
});
