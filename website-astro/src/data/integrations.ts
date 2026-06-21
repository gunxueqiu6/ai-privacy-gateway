export interface Integration {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  setupCode: string;
  setupSteps: string[];
  benefits: string[];
  primaryKeyword: string;
}

const integrations: Integration[] = [
  {
    slug: 'langchain',
    name: 'LangChain',
    tagline: 'Add PII masking to your LangChain pipelines without changing a line of chain code',
    description:
      'LangChain is the most popular framework for building LLM applications. AI Privacy Gateway integrates as a drop-in proxy — just change the base URL in your ChatOpenAI or ChatAnthropic configuration.',
    setupCode: `from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    base_url="http://localhost:9999/v1",  # Route through privacy gateway
    api_key="your-api-key"
)`,
    setupSteps: [
      'Start the gateway: docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite',
      'Change base_url in your ChatOpenAI/ChatAnthropic init to http://localhost:9999/v1',
      'All PII in prompts and messages is now automatically masked',
    ],
    benefits: [
      'No chain code changes — works with all existing LangChain components',
      'Protects all model providers (OpenAI, Anthropic, DeepSeek, etc.)',
      'Works with streaming, batch, and async LangChain operations',
    ],
    primaryKeyword: 'LangChain PII masking proxy integration',
  },
  {
    slug: 'openai-sdk',
    name: 'OpenAI SDK',
    tagline: 'Protect your OpenAI API calls with zero code changes',
    description:
      'The OpenAI Python and Node.js SDKs are the most common way applications interact with AI. AI Privacy Gateway is fully OpenAI-API-compatible — just change the base URL.',
    setupCode: `from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",  # Proxy through privacy gateway
    api_key="your-openai-api-key"
)

# All PII in messages is auto-masked before reaching OpenAI
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "..."}]
)`,
    setupSteps: [
      'Deploy gateway: docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite',
      'Set base_url="http://localhost:9999/v1" in OpenAI() client init',
      'Your OpenAI API key still works — gateway transparently forwards it',
    ],
    benefits: [
      '100% OpenAI API compatible — drop-in replacement base URL',
      'Streaming, function calling, and vision all supported',
      'Works with any OpenAI-compatible provider (DeepSeek, Groq, etc.)',
    ],
    primaryKeyword: 'OpenAI SDK PII masking privacy proxy',
  },
  {
    slug: 'anthropic-sdk',
    name: 'Anthropic SDK',
    tagline: 'Use Claude safely — mask sensitive data before it reaches Anthropic',
    description:
      'The Anthropic SDK for Claude models integrates seamlessly with AI Privacy Gateway. Route your messages through the privacy proxy to ensure no PII reaches Anthropic servers.',
    setupCode: `import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:9999/v1",  # Route through privacy gateway
    api_key="your-anthropic-api-key"
)

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}]
)`,
    setupSteps: [
      'Deploy gateway: docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite',
      'Set base_url in Anthropic() client to http://localhost:9999/v1',
      'Gateway auto-masks PII, forwards clean prompt to Anthropic API',
    ],
    benefits: [
      'Protect proprietary code sent to Claude for analysis',
      'Full Claude Messages API compatibility',
      'Streaming, tool use, and vision all supported',
    ],
    primaryKeyword: 'Anthropic Claude SDK privacy proxy PII masking',
  },
  {
    slug: 'llamaindex',
    name: 'LlamaIndex',
    tagline: 'Secure your RAG pipelines — mask PII before embedding and generation',
    description:
      'LlamaIndex RAG applications often process sensitive documents. AI Privacy Gateway ensures PII is masked both during embedding and during LLM generation — without changing your LlamaIndex code.',
    setupCode: `from llama_index.llms.openai import OpenAI

llm = OpenAI(
    model="gpt-4o",
    api_base="http://localhost:9999/v1",  # Route through privacy gateway
    api_key="your-api-key"
)`,
    setupSteps: [
      'Deploy the privacy gateway as a Docker container',
      'Set api_base="http://localhost:9999/v1" in your LlamaIndex LLM config',
      'Documents are now PII-masked before embedding and generation',
    ],
    benefits: [
      'Protects sensitive documents in RAG pipelines',
      'Works with all LlamaIndex LLM backends',
      'No changes to ingestion or query pipelines',
    ],
    primaryKeyword: 'LlamaIndex RAG PII masking privacy proxy',
  },
  {
    slug: 'semantic-kernel',
    name: 'Semantic Kernel',
    tagline: 'Microsoft Semantic Kernel with enterprise-grade AI data protection',
    description:
      'Semantic Kernel is Microsoft\'s AI orchestration framework. Route it through AI Privacy Gateway to add PII masking to all your AI plugins and planners.',
    setupCode: `// In your Semantic Kernel configuration
var kernel = Kernel.CreateBuilder()
    .AddOpenAIChatCompletion(
        modelId: "gpt-4o",
        endpoint: new Uri("http://localhost:9999/v1"),  // Privacy gateway
        apiKey: "your-api-key"
    )
    .Build();`,
    setupSteps: [
      'Deploy gateway: docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite',
      'Configure your Semantic Kernel OpenAI/OpenAI-compatible endpoint to localhost:9999/v1',
      'All plugin and planner prompts are now PII-masked',
    ],
    benefits: [
      'Enterprise-grade data protection for .NET AI apps',
      'Works with Semantic Kernel planners, plugins, and functions',
      'Drop-in endpoint change — zero plugin code changes',
    ],
    primaryKeyword: 'Semantic Kernel AI privacy data protection .NET',
  },
  {
    slug: 'claude-code',
    name: 'Claude Code',
    tagline: 'Stop Claude Code from reading your proprietary source code raw',
    description:
      'Claude Code is Anthropic\'s agentic coding tool that reads your entire codebase. AI Privacy Gateway masks sensitive patterns in your code before they reach Anthropic\'s servers.',
    setupCode: `# Set environment variable to route through gateway
export ANTHROPIC_BASE_URL="http://localhost:9999/v1"

# Or configure in Claude Code settings
claude config set ANTHROPIC_BASE_URL "http://localhost:9999/v1"`,
    setupSteps: [
      'Deploy gateway: docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite',
      'Set ANTHROPIC_BASE_URL=http://localhost:9999/v1',
      'Run Claude Code normally — PII and secrets in code are auto-masked',
    ],
    benefits: [
      'Protect API keys, tokens, and secrets embedded in code',
      'Mask PII in test fixtures and database seeds',
      'Keep proprietary algorithms confidential from AI analysis',
    ],
    primaryKeyword: 'Claude Code privacy protect source code API keys',
  },
  {
    slug: 'cursor-ide',
    name: 'Cursor IDE',
    tagline: 'Use Cursor without sending your entire codebase to the cloud unprotected',
    description:
      'Cursor IDE sends code context to AI providers for completions and chat. Route through AI Privacy Gateway to ensure sensitive data in your codebase stays protected.',
    setupCode: `# Cursor respects the OPENAI_BASE_URL environment variable
export OPENAI_BASE_URL="http://localhost:9999/v1"

# Or configure per-project .cursorrules`,
    setupSteps: [
      'Start the privacy gateway locally',
      'Set OPENAI_BASE_URL to point to your gateway',
      'Cursor completions and chat are now PII-masked',
    ],
    benefits: [
      'Protect proprietary code from being sent to AI servers',
      'Auto-mask secrets and tokens in code comments and strings',
      'Zero impact on Cursor\'s autocomplete speed',
    ],
    primaryKeyword: 'Cursor IDE privacy protect source code cloud',
  },
  {
    slug: 'continue-dev',
    name: 'Continue.dev',
    tagline: 'Open-source AI code assistant with built-in privacy protection',
    description:
      'Continue.dev is the leading open-source AI code assistant. Configure it to route through AI Privacy Gateway for automatic PII and secret masking in all AI interactions.',
    setupCode: `// In continue config.json
{
  "models": [{
    "title": "GPT-4 (Privacy Protected)",
    "provider": "openai",
    "model": "gpt-4o",
    "apiBase": "http://localhost:9999/v1",  // Privacy gateway
    "apiKey": "your-api-key"
  }]
}`,
    setupSteps: [
      'Deploy the privacy gateway locally: docker run -d -p 9999:9999 ...',
      'In Continue config, set "apiBase" to "http://localhost:9999/v1"',
      'Continue.dev now sends masked code context to AI providers',
    ],
    benefits: [
      'Open source + open source — full transparency',
      'Works with any model provider in Continue',
      'Protects code, comments, and config files',
    ],
    primaryKeyword: 'Continue.dev AI privacy open source code assistant',
  },
];

export default integrations;
