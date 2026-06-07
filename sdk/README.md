# AI Privacy Gateway SDK

## JS/TS SDK (`sdk/js`)

npm package for client-side PII masking and gateway proxy integration.

### Install

```bash
npm install @privacygw/sdk
```

### Usage

```ts
import { mask, GatewayClient } from '@privacygw/sdk';

// Client-side pre-check
const { text, masked } = mask('我的手机13812345678，邮箱user@example.com');
// text: "我的手机[VAULT_PH_abc12345]，邮箱[VAULT_EM_def67890]"
// masked: ["13812345678", "user@example.com"]

// Gateway proxy client (server-side masking)
const client = new GatewayClient({ baseUrl: 'http://localhost:9999' });
const resp = await client.chatCompletion({
  messages: [{ role: 'user', content: '我的手机13812345678' }],
});
```

### Build

```bash
cd sdk/js && npm install && npm run build
```

## Browser Extension (`sdk/browser-extension`)

Chrome/Edge extension that auto-routes LLM API calls through your privacy gateway.

### Install (dev)

1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" → select `sdk/browser-extension/`
4. Set your gateway URL in the popup

### Supported LLM APIs

- OpenAI (`api.openai.com`)
- DeepSeek (`api.deepseek.com`)
- Anthropic (`api.anthropic.com`)
- Google Gemini (`generativelanguage.googleapis.com`)
