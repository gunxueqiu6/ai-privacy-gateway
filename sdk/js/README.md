# @privacygw/sdk

AI Privacy Gateway JavaScript SDK - Protect your sensitive data when interacting with AI services

## Installation

```bash
npm install @privacygw/sdk
# or
yarn add @privacygw/sdk
```

## Quick Start

```javascript
import { PrivacyGateway } from '@privacygw/sdk';

const gateway = new PrivacyGateway({
  baseUrl: 'http://localhost:9999',
  timeout: 10000
});

// Single text masking
const result = await gateway.mask('张三住在北京市海淀区，电话13812345678');
console.log(result.masked_text);
console.log(result.entities);

// Restore text
const restored = await gateway.restore(result.masked_text, {
  '[PII_PER_00000001]': '张三',
  '[PII_LOC_00000002]': '北京市海淀区',
  '[PII_PHONE_00000003]': '13812345678'
});
console.log(restored.original_text);

// Batch masking
const batchResult = await gateway.maskBatch([
  '联系电话13900001111',
  '邮箱test@example.com'
]);
console.log(batchResult.results);

// Get supported entities
const entities = await gateway.getEntities();
console.log(entities);
```

## API

### `new PrivacyGateway(config)`

Create a new gateway instance.

**Config options:**
- `baseUrl` (required): Gateway server URL
- `timeout` (optional): Request timeout in ms (default: 10000)
- `headers` (optional): Custom headers

### `gateway.mask(text)`

Mask sensitive information in text.

**Returns:**
```typescript
{
  masked_text: string;
  entities: Array<{
    type: string;
    value: string;
    placeholder: string;
    position?: number;
  }>;
  stats: Record<string, number>;
}
```

### `gateway.restore(maskedText, mappings)`

Restore masked text to original.

**Parameters:**
- `maskedText`: The masked text
- `mappings`: Object mapping placeholders to original values

**Returns:**
```typescript
{
  original_text: string;
}
```

### `gateway.maskBatch(texts)`

Batch mask multiple texts.

**Parameters:**
- `texts`: Array of texts (max 50)

**Returns:**
```typescript
{
  results: Array<{
    original: string;
    masked: string;
    entities: Array<{ type, value, placeholder }>;
    stats: Record<string, number>;
  }>;
  total_count: number;
}
```

### `gateway.getEntities()`

Get supported entity types.

**Returns:**
```typescript
{
  entities: Array<{
    type: string;
    name: string;
    description: string;
    enabled: boolean;
  }>;
  total: number;
  version: string;
}
```

### `gateway.detectEntities(text)`

Client-side entity detection (no server call).

**Returns:**
```typescript
Array<{
  type: string;
  value: string;
  placeholder: string;
  position: number;
}>
```

## Supported Entity Types

| Type | Name | Description |
|------|------|-------------|
| PII_PHONE | 手机号 | 中国大陆手机号 |
| PII_EMAIL | 邮箱 | 电子邮箱地址 |
| PII_IDCARD | 身份证 | 中国身份证号码 |
| PII_BANK | 银行卡 | 银行卡号码 |
| PII_PER | 人名 | 中文人名 |
| PII_LOC | 地名 | 省份、城市等 |
| PII_ORG | 机构名 | 公司、组织名称 |
| PII_PLATE | 车牌号 | 中国车牌号 |
| PII_IP | IP地址 | IPv4 地址 |
| PII_URL | URL | 网址链接 |
| PII_DATE | 日期 | 日期格式 |
| PII_AMOUNT | 金额 | 货币金额 |
| PII_POSTCODE | 邮编 | 邮政编码 |
| PII_CUST | 自定义 | 自定义敏感词 |

## License

MIT