export const LANGUAGES = {
  en: { label: 'English', flag: 'EN' },
  zh: { label: '中文', flag: '中文' },
} as const;

export type Lang = keyof typeof LANGUAGES;

export const DEFAULT_LANG: Lang = 'zh';

export const LANG_MAP: Record<string, Lang> = {
  zh: 'zh',
  'zh-CN': 'zh',
  'zh-TW': 'zh',
  en: 'en',
  'en-US': 'en',
  'en-GB': 'en',
};

export function detectLang(acceptLanguage?: string): Lang {
  if (!acceptLanguage) return DEFAULT_LANG;
  const langs = acceptLanguage.split(',').map(s => s.split(';')[0].trim());
  for (const lang of langs) {
    const mapped = LANG_MAP[lang];
    if (mapped) return mapped;
  }
  return DEFAULT_LANG;
}
