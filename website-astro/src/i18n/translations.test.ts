import { describe, it, expect } from 'vitest';
import { t } from './translations';

describe('t() translation function', () => {
  it('returns Chinese string for zh nav.home', () => {
    expect(t('zh', 'nav.home')).toBe('首页');
  });

  it('returns English string for en nav.home', () => {
    expect(t('en', 'nav.home')).toBe('Home');
  });

  it('returns Chinese string for zh nav.demo', () => {
    expect(t('zh', 'nav.demo')).toBe('演示');
  });

  it('returns English string for en nav.demo', () => {
    expect(t('en', 'nav.demo')).toBe('Demo');
  });

  it('returns Chinese string for deeply nested key', () => {
    expect(t('zh', 'pricing.hero_title2')).toBe('只需隐私。');
  });

  it('returns English string for deeply nested key', () => {
    expect(t('en', 'pricing.hero_title2')).toBe('Just privacy.');
  });

  it('returns Chinese string for demo section key', () => {
    expect(t('zh', 'demo.mask_btn')).toBe('脱敏处理');
  });

  it('returns English string for demo section key', () => {
    expect(t('en', 'demo.mask_btn')).toBe('Mask PII');
  });

  it('returns the key itself for nonexistent key when en also lacks it', () => {
    expect(t('en', 'nonexistent.key')).toBe('nonexistent.key');
  });

  it('falls back to English when key exists in en but not in zh', () => {
    // 'nonexistent' doesn't exist in either
    expect(t('zh', 'nonexistent.deeply.nested')).toBe('nonexistent.deeply.nested');
  });

  it('returns key for completely invalid key path', () => {
    expect(t('zh', '')).toBe('');
  });

  it('handles footer section keys correctly', () => {
    expect(t('zh', 'footer.copyright')).toBe('AI Privacy Gateway. MIT Licensed. Open Source.');
    expect(t('en', 'footer.copyright')).toBe('AI Privacy Gateway. MIT Licensed. Open Source.');
  });

  it('handles lang_switcher section keys', () => {
    expect(t('zh', 'lang_switcher.zh')).toBe('中文');
    expect(t('en', 'lang_switcher.zh')).toBe('中文');
  });

  it('handles home section keys', () => {
    expect(t('zh', 'home.title_line1')).toBe('你的 AI 数据正在裸奔');
    expect(t('en', 'home.title_line1')).toBe('Your AI data is leaking');
  });

  it('handles docs section keys', () => {
    expect(t('zh', 'docs.title')).toBe('技术文档');
    expect(t('en', 'docs.title')).toBe('Documentation');
  });
});
