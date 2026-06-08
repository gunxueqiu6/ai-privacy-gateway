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
  });

  describe('error handling', () => {
    it('should throw on non-ok response', async () => {
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
  });
});