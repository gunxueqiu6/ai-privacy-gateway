const DEFAULT_PATTERNS: [RegExp, string | ((m: string) => string)][] = [
  [/1[3-9]\d{9}/g, (m: string) => `[VAULT_PH_${hash8(m)}]`],
  [/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, (m: string) => `[VAULT_EM_${hash8(m)}]`],
  [/[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]/g, (m: string) => `[VAULT_ID_${hash8(m)}]`],
  [/\d{16,19}/g, (m: string) => `[VAULT_CARD_${hash8(m)}]`],
];

function hash8(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(16).padStart(8, '0').slice(0, 8);
}

export interface MaskResult {
  text: string;
  masked: string[];
}

export function mask(text: string, extraPatterns?: [RegExp, string | ((m: string) => string)][]): MaskResult {
  const patterns = [...DEFAULT_PATTERNS, ...(extraPatterns || [])];
  const seen: string[] = [];
  let result = text;
  for (const [re, replacement] of patterns) {
    result = result.replace(re, (match) => {
      seen.push(match);
      return typeof replacement === 'function' ? replacement(match) : replacement;
    });
  }
  return { text: result, masked: seen };
}

export function addPattern(re: RegExp, replacement: string | ((m: string) => string)): void {
  DEFAULT_PATTERNS.push([re, replacement as (m: string) => string]);
}
