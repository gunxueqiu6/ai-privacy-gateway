import { PrivacyGateway } from '../src/index';

// Mock fetch for testing
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('PrivacyGateway', () => {
  let gateway: PrivacyGateway;

  beforeEach(() => {
    gateway = new PrivacyGateway({
      baseUrl: 'http://localhost:9999',
      timeout: 10000
    });
    mockFetch.mockClear();
  });

  describe('mask()', () => {
    it('should mask text successfully', async () => {
      const mockResponse = {
        masked_text: '[PII_PHONE_00000001]',
        entities: [{ type: 'PII_PHONE', value: '13812345678', placeholder: '[PII_PHONE_00000001]', position: 0 }],
        stats: { phone: 1 }
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await gateway.mask('13812345678');

      expect(result.masked_text).toBe('[PII_PHONE_00000001]');
      expect(result.entities.length).toBe(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:9999/api/mask',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ text: '13812345678' })
        })
      );
    });

    it('should throw error for empty text', async () => {
      await expect(gateway.mask('')).rejects.toThrow('text must be a non-empty string');
    });

    it('should throw error for non-string input', async () => {
      await expect(gateway.mask(null as any)).rejects.toThrow('text must be a non-empty string');
    });

    it('should handle network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(gateway.mask('test')).rejects.toThrow('Network error');
    });

    it('should handle timeout', async () => {
      mockFetch.mockImplementationOnce(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('AbortError')), 100)
        )
      );

      await expect(gateway.mask('test')).rejects.toThrow();
    });
  });

  describe('restore()', () => {
    it('should restore masked text successfully', async () => {
      const mockResponse = {
        original_text: '13812345678'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await gateway.restore('[PII_PHONE_00000001]', {
        '[PII_PHONE_00000001]': '13812345678'
      });

      expect(result.original_text).toBe('13812345678');
    });

    it('should throw error for empty maskedText', async () => {
      await expect(gateway.restore('', {})).rejects.toThrow('maskedText must be a non-empty string');
    });
  });

  describe('maskBatch()', () => {
    it('should batch mask texts successfully', async () => {
      const mockResponse = {
        results: [
          { original: 'text1', masked: 'masked1', entities: [], stats: {} },
          { original: 'text2', masked: 'masked2', entities: [], stats: {} }
        ],
        total_count: 2
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await gateway.maskBatch(['text1', 'text2']);

      expect(result.total_count).toBe(2);
      expect(result.results.length).toBe(2);
    });

    it('should throw error for empty array', async () => {
      await expect(gateway.maskBatch([])).rejects.toThrow('texts must be a non-empty array');
    });

    it('should throw error for array exceeding 50 items', async () => {
      const texts = Array(51).fill('test');
      await expect(gateway.maskBatch(texts)).rejects.toThrow('Maximum 50 texts per batch');
    });
  });

  describe('getEntities()', () => {
    it('should get entities list successfully', async () => {
      const mockResponse = {
        entities: [
          { type: 'PII_PHONE', name: '手机号', description: '中国大陆手机号', enabled: true }
        ],
        total: 14,
        version: '2.0'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await gateway.getEntities();

      expect(result.total).toBe(14);
      expect(result.entities.length).toBe(1);
    });
  });

  describe('detectEntities()', () => {
    it('should detect phone number locally', () => {
      const entities = gateway.detectEntities('我的手机号是13812345678');

      expect(entities.length).toBeGreaterThan(0);
      expect(entities[0].type).toBe('PII_PHONE');
      expect(entities[0].value).toBe('13812345678');
    });

    it('should detect email locally', () => {
      const entities = gateway.detectEntities('联系我test@example.com');

      expect(entities.length).toBeGreaterThan(0);
      expect(entities[0].type).toBe('PII_EMAIL');
      expect(entities[0].value).toBe('test@example.com');
    });

    it('should detect multiple entities', () => {
      const entities = gateway.detectEntities('手机13812345678邮箱test@example.com');

      expect(entities.length).toBe(2);
    });

    it('should return empty array for no entities', () => {
      const entities = gateway.detectEntities('这是一段普通文本');

      expect(entities.length).toBe(0);
    });
  });
});