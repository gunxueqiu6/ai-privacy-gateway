# Dify AI Chatbot Configuration — Privacy Gateway

This document covers configuring a Dify AI knowledge base and chatbot for the Privacy Gateway website.

## Dify Knowledge Base Setup

### 1. Create a Knowledge Base

1. Log in to your Dify dashboard
2. Navigate to **Knowledge** > **Create Knowledge**
3. Upload product documentation, feature descriptions, FAQ content, and architecture docs
4. Recommended file types: `.md`, `.pdf`, `.txt`, `.html`

### 2. Knowledge Base Structure

Organize knowledge content into these segments:

| Segment | Content |
|---------|---------|
| Product Overview | What is AI Privacy Gateway, core value proposition |
| Installation Guide | Docker deployment, one-click install, configuration steps |
| Feature Documentation | PII detection types, masking rules, API proxy mode, Cursor/DeepSeek/Kimi integration |
| FAQ | Common questions about privacy, deployment, pricing, supported models |
| Troubleshooting | Known issues, error codes, solutions |
| API Reference | Endpoint descriptions, request/response examples |

### 3. Chunking Settings

- **Chunk size**: 500-1000 tokens per chunk
- **Chunk overlap**: 100-200 tokens
- **Index mode**: `High Quality` (Embedding + Keyword) for best results
- **Retrieval strategy**: `Hybrid Search` (vector + keyword)

### 4. Creating the Chatbot (Dify App)

1. Navigate to **Studio** > **Create Application** > **Chatbot**
2. Select the knowledge base you created
3. **Model**: GPT-4o or Claude 3.5 Sonnet recommended for best responses
4. **Prompt**: Provide a system prompt

Example system prompt:

```
You are a helpful product assistant for AI Privacy Gateway. Your role is to:
- Answer questions about the product's features, installation, and configuration
- Help users understand how privacy gateway protects their AI data
- Provide accurate technical guidance based on the knowledge base
- Be concise and clear in your responses
- If you cannot find an answer in the knowledge base, politely say so and offer to connect the user with support

Always maintain a helpful and professional tone. Keep responses focused on the product.
```

## API Endpoint Setup

### 1. Get API Credentials

1. In Dify Studio, open your chatbot app
2. Go to **API Access**
3. Copy the **API Server URL** (typically `https://your-dify-instance.com/v1`)
4. Copy the **API Secret Key** (format: `app-xxxxxxxxxxxxx`)

### 2. Environment Variables

Add to `website-astro/.env`:

```bash
# Dify AI Chatbot
PUBLIC_DIFY_API_URL=https://your-dify-instance.com/v1
PUBLIC_DIFY_API_KEY=app-xxxxxxxxxxxxx
```

These are public-facing environment variables prefixed with `PUBLIC_` because the Astro static site needs them at build time. The API key should have restricted permissions in Dify (only the chatbot app scope).

## Embedding on the Website

The chatbot component is already built at `src/components/DifyChat.astro`. Include it in any page layout:

```astro
---
import DifyChat from '../components/DifyChat.astro';
---
<!-- Page content -->

<DifyChat />
```

If you need to override the defaults at a specific page:

```astro
<DifyChat apiUrl="https://custom-instance.com/v1" apiKey="app-xxxxxxxxxxxxx" />
```

## Testing

1. Deploy the updates
2. Open the website
3. Click the green chat bubble (bottom-right corner)
4. Type test questions:
   - "How do I install Privacy Gateway?"
   - "What types of PII can it detect?"
   - "Does it work with DeepSeek?"
   - "How is my data protected?"

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Chat shows "not configured" | Missing `PUBLIC_DIFY_API_URL` | Check `.env` file |
| 401 Unauthorized | Invalid API key | Regenerate key in Dify |
| No response from server | Network/firewall blocking Dify | Check instance reachability |
| Irrelevant answers | Knowledge base content insufficient | Add more product docs to knowledge base |
