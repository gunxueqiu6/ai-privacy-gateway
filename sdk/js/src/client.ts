export interface GatewayOptions {
  baseUrl: string;
  apiKey?: string;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatCompletionRequest {
  messages: ChatMessage[];
  model?: string;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatCompletionChoice {
  index: number;
  message: ChatMessage;
  finish_reason: string;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
}

export interface MaskResult {
  masked_text: string;
  entities: Array<{ type: string; value: string; placeholder: string; position?: number }>;
  stats: Record<string, number>;
}

export interface RestoreResult {
  original_text: string;
}

export interface BatchMaskResult {
  results: Array<{ original: string; masked: string; entities: unknown[]; stats: Record<string, number> }>;
  total_count: number;
}

export interface EntityType {
  type: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface EntitiesResponse {
  entities: EntityType[];
  total: number;
  version: string;
}

export class GatewayClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(options: GatewayOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
  }

  private get headers(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
    };
  }

  private async request<T>(path: string, method: 'GET' | 'POST' = 'GET', body?: Record<string, unknown>): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Gateway error ${res.status}: ${text}`);
    }
    return res.json();
  }

  async mask(text: string): Promise<MaskResult> {
    if (!text || typeof text !== 'string') {
      throw new Error('text must be a non-empty string');
    }
    return this.request<MaskResult>('/api/mask', 'POST', { text });
  }

  async restore(maskedText: string, mappings?: Record<string, string>): Promise<RestoreResult> {
    if (!maskedText || typeof maskedText !== 'string') {
      throw new Error('maskedText must be a non-empty string');
    }
    return this.request<RestoreResult>('/api/restore', 'POST', { text: maskedText, mappings });
  }

  async maskBatch(texts: string[]): Promise<BatchMaskResult> {
    if (!Array.isArray(texts) || texts.length === 0) {
      throw new Error('texts must be a non-empty array');
    }
    if (texts.length > 50) {
      throw new Error('Maximum 50 texts per batch');
    }
    return this.request<BatchMaskResult>('/api/mask/batch', 'POST', { texts });
  }

  async getEntities(): Promise<EntitiesResponse> {
    return this.request<EntitiesResponse>('/api/entities');
  }

  async chatCompletion(req: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ ...req, stream: false }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Gateway error ${res.status}: ${body}`);
    }
    return res.json();
  }

  async *chatCompletionStream(req: ChatCompletionRequest): AsyncGenerator<string, void, unknown> {
    const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ ...req, stream: true }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Gateway error ${res.status}: ${body}`);
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error('No response body');
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          yield data;
        }
      }
    }
  }
}
