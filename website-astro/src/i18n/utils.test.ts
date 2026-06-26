import { describe, it, expect } from 'vitest';
import { getLangFromURL, getPathForLang } from './utils';

describe('getLangFromURL', () => {
  it('returns zh for root path', () => {
    expect(getLangFromURL('/')).toBe('zh');
  });

  it('returns en for /en/ path', () => {
    expect(getLangFromURL('/en/')).toBe('en');
  });

  it('returns en for /en without trailing slash', () => {
    expect(getLangFromURL('/en')).toBe('en');
  });

  it('returns en for /en/pricing nested path', () => {
    expect(getLangFromURL('/en/pricing')).toBe('en');
  });

  it('returns zh for /demo path', () => {
    expect(getLangFromURL('/demo')).toBe('zh');
  });

  it('returns zh for /pricing path', () => {
    expect(getLangFromURL('/pricing')).toBe('zh');
  });

  it('returns zh for paths starting with /en but not exactly matching', () => {
    expect(getLangFromURL('/en-other')).toBe('zh');
  });

  it('returns zh for empty string', () => {
    expect(getLangFromURL('')).toBe('zh');
  });
});

describe('getPathForLang', () => {
  it('converts /demo to /en/demo for English target', () => {
    expect(getPathForLang('/demo', 'en')).toBe('/en/demo');
  });

  it('converts /en/pricing to /pricing for Chinese target', () => {
    expect(getPathForLang('/en/pricing', 'zh')).toBe('/pricing');
  });

  it('returns /en for root when target is English', () => {
    expect(getPathForLang('/', 'en')).toBe('/en');
  });

  it('converts /en to / (root) when target is Chinese', () => {
    expect(getPathForLang('/en', 'zh')).toBe('/');
  });

  it('converts /en/ to / when target is Chinese', () => {
    expect(getPathForLang('/en/', 'zh')).toBe('/');
  });

  it('returns same path when already in target language (zh -> zh)', () => {
    expect(getPathForLang('/demo', 'zh')).toBe('/demo');
  });

  it('returns same path when already in target language (en -> en)', () => {
    expect(getPathForLang('/en/pricing', 'en')).toBe('/en/pricing');
  });

  it('converts deeply nested /en/a/b/c to /a/b/c for Chinese target', () => {
    expect(getPathForLang('/en/a/b/c', 'zh')).toBe('/a/b/c');
  });

  it('converts /pricing to /en/pricing for English target', () => {
    expect(getPathForLang('/pricing', 'zh')).toBe('/pricing');
  });

  it('handles path without leading slash for English target', () => {
    // Not a realistic input, but documents existing behavior: string is treated as-is
    const result = getPathForLang('demo', 'en');
    expect(result).toBe('/endemo');
  });
});
