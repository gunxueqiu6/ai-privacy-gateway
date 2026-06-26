import { GatewayClient } from '../src/client';

// Mock fetch for testing
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('GatewayClient', () => {
  let client: GatewayClient;

  beforeEach(() => {
    client = new GatewayClient({
      baseUrl: 'http://localhost:9999',
      apiKey: 'test-api-key'
    });
    mockFetch.mockClear();
  });

  describe('constructor', () => {
    it('should reject non-HTTPS URLs that are not localhost', () => {
      expect(() => new GatewayClient({ baseUrl: 'http://example.com' })).toThrow(
        'Gateway URL must use HTTPS (localhost allowed for development)'
      );
    });

    it('should reject HTTP IP addresses that are not loopback', () => {
      expect(() => new GatewayClient({ baseUrl: 'http://192.168.1.1' })).toThrow(
        'Gateway URL must use HTTPS (localhost allowed for development)'
      );
    });

    it('should accept HTTPS URLs', () => {
      expect(() => new GatewayClient({ baseUrl: 'https://example.com' })).not.toThrow();
    });

    it('should accept HTTP localhost', () => {
      expect(() => new GatewayClient({ baseUrl: 'http://localhost:9999' })).not.toThrow();
    });

    it('should accept HTTP 127.0.0.1', () => {
      expect(() => new GatewayClient({ baseUrl: 'http://127.0.0.1:8080' })).not.toThrow();
    });

    it('should work without apiKey', async () => {
      const clientNoAuth = new GatewayClient({ baseUrl: 'http://localhost:9999' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ masked_text: 'ok', entities: [], stats: {} })
      });

      const result = await clientNoAuth.mask('test');
      expect(result.masked_text).toBe('ok');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/mask'),
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });
  });

  describe('chatCompletion()', () => {
    it('should send chat completion request', async () => {
      const mockResponse = {
        id: 'chat-123',
        choices: [{ message: { content: 'Hello!' } }]
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await client.chatCompletion({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }]
      });

      expect(result.choices[0].message.content).toBe('Hello!');
    });

    it('should send request with stream:false to gateway', async () => {
      const mockResponse = {
        id: 'chat-123',
        choices: [{ message: { content: 'Hi' } }]
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      await client.chatCompletion({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }],
        stream: true
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/chat/completions'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"stream":false')
        })
      );
    });
  });

  describe('chatCompletionStream()', () => {
    it('should handle streaming request', async () => {
      const encoder = new TextEncoder();
      const chunks = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
        'data: {"choices":[{"delta":{"content":" world"}}]}\n',
        'data: [DONE]\n'
      ];
      const streamData = encoder.encode(chunks.join('\n'));

      let readCount = 0;
      const mockStreamResponse = {
        ok: true,
        body: {
          getReader: () => ({
            read: () => {
              if (readCount === 0) {
                readCount++;
                return Promise.resolve({ done: false, value: streamData });
              }
              return Promise.resolve({ done: true });
            }
          })
        }
      };

      mockFetch.mockResolvedValueOnce(mockStreamResponse);

      const results: string[] = [];
      for await (const chunk of client.chatCompletionStream({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }]
      })) {
        results.push(chunk);
      }

      expect(results.length).toBeGreaterThan(0);
      expect(mockFetch).toHaveBeenCalled();
    });

    it('should throw on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      });

      const gen = client.chatCompletionStream({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }]
      });

      await expect(gen.next()).rejects.toThrow('Gateway error 500');
    });
  });

  describe('mask()', () => {
    it('should call /api/mask and return masked result', async () => {
      const mockResponse = {
        masked_text: '我的手机号是[PII_PHONE_00000001]',
        entities: [{ type: 'PII_PHONE', value: '13812345678', placeholder: '[PII_PHONE_00000001]' }],
        stats: { phone: 1 }
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await client.mask('我的手机号是13812345678');

      expect(result.masked_text).toContain('[PII_PHONE_00000001]');
      expect(result.entities.length).toBe(1);
    });

    it('should throw on empty string', async () => {
      await expect(client.mask('')).rejects.toThrow('text must be a non-empty string');
    });

    it('should throw when text exceeds MAX_TEXT_LENGTH', async () => {
      const longText = 'a'.repeat(102401);
      await expect(client.mask(longText)).rejects.toThrow('text exceeds maximum length');
    });
  });

  describe('restore()', () => {
    it('should restore masked text with mappings', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ original_text: 'Hello 13812345678' })
      });

      const result = await client.restore('Hello [PII_PHONE_00000001]', {
        '[PII_PHONE_00000001]': '13812345678'
      });

      expect(result.original_text).toBe('Hello 13812345678');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/restore'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should throw on empty maskedText', async () => {
      await expect(client.restore('')).rejects.toThrow('maskedText must be a non-empty string');
    });

    it('should throw when maskedText exceeds MAX_TEXT_LENGTH', async () => {
      const longText = 'a'.repeat(102401);
      await expect(client.restore(longText)).rejects.toThrow('maskedText exceeds maximum length');
    });
  });

  describe('maskBatch()', () => {
    it('should batch mask texts', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          results: [{ original: 'text1', masked: 'masked1', entities: [], stats: {} }],
          total_count: 1
        })
      });

      const result = await client.maskBatch(['text1']);
      expect(result.total_count).toBe(1);
    });

    it('should throw on empty array', async () => {
      await expect(client.maskBatch([])).rejects.toThrow('texts must be a non-empty array');
    });

    it('should throw when array exceeds 50 items', async () => {
      await expect(client.maskBatch(Array(51).fill('test'))).rejects.toThrow('Maximum 50 texts per batch');
    });
  });

  describe('getEntities()', () => {
    it('should fetch entities list', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ entities: [], total: 14, version: '2.0' })
      });

      const result = await client.getEntities();
      expect(result.total).toBe(14);
      expect(result.version).toBe('2.0');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/entities'),
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('error handling', () => {
    it('should throw on non-ok response for chatCompletion', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve('Unauthorized'),
        json: () => Promise.resolve({ error: 'Unauthorized' })
      });

      await expect(client.chatCompletion({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }]
      })).rejects.toThrow('Gateway error 401');
    });

    it('should throw on non-ok response for request() via mask', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      });

      await expect(client.mask('test')).rejects.toThrow('Gateway error 500');
    });
  });
});