import { GatewayClient } from '../src/client';

// Mock fetch for testing
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('GatewayClient', () => {
  let client: GatewayClient;

  beforeEach(() => {
    client = new GatewayClient({
      baseUrl: 'http://localhost:9999',
      targetApi: 'https://api.openai.com',
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

    it('should handle streaming request', async () => {
      // Mock streaming response
      const mockStreamResponse = {
        ok: true,
        body: {
          getReader: () => ({
            read: () => Promise.resolve({ done: true, value: new Uint8Array() })
          })
        }
      };

      mockFetch.mockResolvedValueOnce(mockStreamResponse);

      const result = await client.chatCompletion({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hi' }],
        stream: true
      });

      // Verify stream handling
      expect(mockFetch).toHaveBeenCalled();
    });

    it('should mask sensitive data in request', async () => {
      const mockMaskResponse = {
        masked_text: '我的手机号是[PII_PHONE_00000001]',
        entities: [{ type: 'PII_PHONE', value: '13812345678', placeholder: '[PII_PHONE_00000001]' }],
        stats: { phone: 1 }
      };

      const mockChatResponse = {
        id: 'chat-123',
        choices: [{ message: { content: '收到' } }]
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockMaskResponse)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockChatResponse)
        });

      const result = await client.chatCompletion({
        model: 'gpt-4',
        messages: [{ role: 'user', content: '我的手机号是13812345678' }]
      });

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('proxyRequest()', () => {
    it('should proxy generic API request', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ data: 'test' })
      };

      mockFetch.mockResolvedValueOnce(mockResponse);

      await client.proxyRequest('/v1/models', 'GET');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:9999/v1/models',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });
});