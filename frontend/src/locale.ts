import { computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { updatePageMetadata } from './seo';

import { messages, type Locale } from './messages';
export type { Locale } from './messages';
export const LOCALE_STORAGE_KEY = 'support-assistant.locale';

export function getInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (saved === 'en' || saved === 'ru') return saved;
  } catch {
    // Browser privacy settings may disable storage.
  }
  return navigator.language.toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function useLocale() {
  const route = useRoute();
  const router = useRouter();
  const locale = computed<Locale>(() => (route.meta.locale === 'ru' ? 'ru' : 'en'));
  const text = computed(() => messages[locale.value]);
  watch(
    locale,
    (value) => {
      if (typeof document !== 'undefined') updatePageMetadata(value);
    },
    { immediate: true },
  );

  function rememberLocale(value: Locale): void {
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, value);
    } catch {
      // Navigation still works when browser storage is unavailable.
    }
  }
  return { locale, text, rememberLocale, router };
}
