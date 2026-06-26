import type { Lang } from './ui';

export function getLangFromURL(pathname: string): Lang {
  if (pathname.startsWith('/en/') || pathname === '/en') return 'en';
  return 'zh';
}

export function getPathForLang(pathname: string, targetLang: Lang): string {
  const isEn = pathname.startsWith('/en/') || pathname === '/en';
  if (targetLang === 'en' && !isEn) return '/en' + (pathname === '/' ? '' : pathname);
  if (targetLang === 'zh' && isEn) return pathname.replace(/^\/en/, '') || '/';
  return pathname;
}
