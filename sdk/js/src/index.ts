import {
  Entity,
  MaskResult,
  RestoreResult,
  BatchMaskResponse,
  EntitiesResponse,
  GatewayConfig,
  ErrorResponse
} from './types';

export class PrivacyGateway {
  private baseUrl: string;
  private timeout: number;
  private headers: Record<string, string>;

  constructor(config: GatewayConfig) {
    this.baseUrl = config.baseUrl;
    this.timeout = config.timeout || 10000;
    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers
    };
  }

  private async request<T>(
    path: string,
    method: 'GET' | 'POST' = 'GET',
    body?: Record<string, unknown>
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json() as ErrorResponse;
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json() as T;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  async mask(text: string): Promise<MaskResult> {
    if (!text || typeof text !== 'string') {
      throw new Error('text must be a non-empty string');
    }

    return this.request<MaskResult>('/api/mask', 'POST', { text });
  }

  async restore(maskedText: string, mappings: Record<string, string>): Promise<RestoreResult> {
    if (!maskedText || typeof maskedText !== 'string') {
      throw new Error('maskedText must be a non-empty string');
    }

    return this.request<RestoreResult>('/api/restore', 'POST', {
      text: maskedText,
      mappings
    });
  }

  async maskBatch(texts: string[]): Promise<BatchMaskResponse> {
    if (!Array.isArray(texts) || texts.length === 0) {
      throw new Error('texts must be a non-empty array');
    }

    if (texts.length > 50) {
      throw new Error('Maximum 50 texts per batch');
    }

    return this.request<BatchMaskResponse>('/api/mask/batch', 'POST', { texts });
  }

  async getEntities(): Promise<EntitiesResponse> {
    return this.request<EntitiesResponse>('/api/entities');
  }

  detectEntities(text: string): Entity[] {
    const entities: Entity[] = [];
    
    const patterns: Record<string, RegExp> = {
      PII_PHONE: /(?<!\d)(1[3-9]\d{9})(?!\d)/g,
      PII_EMAIL: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
      PII_IDCARD: /(?<!\d)([1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)/g,
      PII_BANK: /(?<!\d)([1-9]\d{15,18})(?!\d)/g,
      PII_IP: /(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/g,
      PII_URL: /https?:\/\/[^\s]+/g,
    };

    let placeholderCounter = 0;

    for (const [type, pattern] of Object.entries(patterns)) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        placeholderCounter++;
        entities.push({
          type,
          value: match[0],
          placeholder: `[${type}_${String(placeholderCounter).padStart(8, '0')}]`,
          position: match.index
        });
      }
    }

    return entities.sort((a, b) => (a.position || 0) - (b.position || 0));
  }
}

export {
  Entity,
  MaskResult,
  RestoreResult,
  BatchMaskResult,
  BatchMaskResponse,
  EntityType,
  EntitiesResponse,
  GatewayConfig
};

export default PrivacyGateway;