export interface Competitor {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
  comparisonPoints: { label: string; them: string; us: string }[];
  primaryKeyword: string;
}

const competitors: Competitor[] = [
  {
    slug: 'pasteguard',
    name: 'PasteGuard',
    tagline: 'Browser-based PII redaction for web AI chat interfaces',
    description:
      'PasteGuard is a browser extension that redacts PII from text before pasting into AI chat interfaces. It works client-side in the browser, focusing on the copy-paste workflow for individual users.',
    strengths: [
      'Simple browser extension installation',
      'Works with any web-based AI chat',
      'No server infrastructure needed',
    ],
    weaknesses: [
      'Browser-only — no API proxy, no SDK integration',
      'No enterprise deployment model',
      'Limited to manual paste interactions — cannot protect API calls',
    ],
    comparisonPoints: [
      { label: 'Deployment', them: 'Browser extension only', us: 'Docker, binary, browser extension, SDK' },
      { label: 'API Protection', them: 'Not supported', us: 'Full proxy — intercepts all API calls' },
      { label: 'PII Entities', them: '~8 types', us: '14+ types including Chinese-specific formats' },
      { label: 'Latency', them: 'Instant (local JS)', us: '<1ms (local Rust engine)' },
      { label: 'License', them: 'Proprietary', us: 'MIT Open Source' },
    ],
    primaryKeyword: 'PasteGuard alternative open source',
  },
  {
    slug: 'llm-guard',
    name: 'LLM Guard',
    tagline: 'Open-source security toolkit for LLM interactions',
    description:
      'LLM Guard is an open-source Python library that provides input/output sanitization, PII detection, and prompt injection detection for LLM applications.',
    strengths: [
      'Comprehensive sanitization features (PII, prompt injection, toxicity)',
      'Open source with active community',
      'Well-documented Python API',
    ],
    weaknesses: [
      'Library-only — no standalone proxy or gateway',
      'Requires code changes to integrate',
      'Python-only — no cross-language SDK',
    ],
    comparisonPoints: [
      { label: 'Architecture', them: 'Python library (require code integration)', us: 'Standalone proxy (no code changes)' },
      { label: 'Integration', them: 'pip install + add to code', us: '30-second Docker deploy, change base URL' },
      { label: 'Performance', them: 'Python-based detection', us: 'Rust engine — 10x faster' },
      { label: 'PII Entities', them: 'Standard Western formats', us: '14+ types with Chinese ID, phone formats' },
      { label: 'License', them: 'MIT', us: 'MIT' },
    ],
    primaryKeyword: 'LLM Guard vs AI Privacy Gateway',
  },
  {
    slug: 'prompt-guardian',
    name: 'Prompt Guardian',
    tagline: 'Enterprise prompt security and PII scanning platform',
    description:
      'Prompt Guardian is a commercial enterprise platform for scanning prompts for PII, secrets, and compliance violations before they reach AI providers.',
    strengths: [
      'Enterprise compliance reporting',
      'SOC 2 certified platform',
      'Managed cloud service available',
    ],
    weaknesses: [
      'Closed source, proprietary licensing',
      'Cloud-based — data passes through their infrastructure',
      'High cost for enterprise tier',
    ],
    comparisonPoints: [
      { label: 'Data Privacy', them: 'Data passes through their cloud', us: '100% local — data never leaves your infra' },
      { label: 'Deployment', them: 'Cloud or on-prem (enterprise only)', us: 'Self-hosted in 30 seconds, any environment' },
      { label: 'Pricing', them: 'Per-seat enterprise pricing', us: 'Free Lite, affordable Pro/Enterprise' },
      { label: 'Open Source', them: 'Proprietary', us: 'MIT — full source available' },
      { label: 'License', them: 'Proprietary', us: 'MIT Open Source' },
    ],
    primaryKeyword: 'Prompt Guardian alternative self-hosted',
  },
  {
    slug: 'guardrails-ai',
    name: 'Guardrails AI',
    tagline: 'Validation framework for LLM outputs',
    description:
      'Guardrails AI provides a framework for defining and enforcing structural, type, and quality constraints on LLM outputs using RAIL spec.',
    strengths: [
      'Structured output validation with RAIL spec',
      'Good for ensuring output quality',
      'Open source Python library',
    ],
    weaknesses: [
      'Output-focused — limited input/PII sanitization',
      'Library integration required',
      'No standalone proxy deployment',
    ],
    comparisonPoints: [
      { label: 'Focus', them: 'Output validation and structure', us: 'Input PII masking + output unmasking' },
      { label: 'Deployment', them: 'pip install + code integration', us: '30-second Docker, zero code changes' },
      { label: 'PII Protection', them: 'Not primary focus', us: 'Core feature — 14+ entity types' },
      { label: 'Latency', them: 'Python framework overhead', us: '<1ms Rust engine' },
      { label: 'License', them: 'Apache 2.0', us: 'MIT' },
    ],
    primaryKeyword: 'Guardrails AI PII masking comparison',
  },
  {
    slug: 'lakera-guard',
    name: 'Lakera Guard',
    tagline: 'AI security for prompt injection and data loss prevention',
    description:
      'Lakera Guard provides an API-first security layer for LLM applications, focusing on prompt injection detection and sensitive data detection.',
    strengths: [
      'Strong prompt injection detection',
      'API-based — easy to add to existing apps',
      'Real-time threat intelligence',
    ],
    weaknesses: [
      'Cloud API required — data leaves your infrastructure',
      'Closed source',
      'Per-request pricing can be expensive at scale',
    ],
    comparisonPoints: [
      { label: 'Data Residency', them: 'Data sent to Lakera cloud', us: '100% local processing — zero data egress' },
      { label: 'Pricing', them: 'Per-API-call pricing', us: 'Free Lite, flat Pro/Enterprise pricing' },
      { label: 'Prompt Injection', them: 'Excellent detection', us: 'Basic detection + PII masking as primary feature' },
      { label: 'Self-Hosted', them: 'Not available', us: 'Docker, binary, browser extension' },
      { label: 'License', them: 'Proprietary SaaS', us: 'MIT Open Source' },
    ],
    primaryKeyword: 'Lakera Guard self-hosted alternative',
  },
  {
    slug: 'nightfall-ai',
    name: 'Nightfall AI',
    tagline: 'Cloud DLP platform for SaaS and AI applications',
    description:
      'Nightfall is a cloud-native data loss prevention (DLP) platform that scans for sensitive data across SaaS apps, cloud infrastructure, and AI tools.',
    strengths: [
      'Broad DLP coverage across many SaaS tools',
      'Enterprise compliance certifications',
      'Managed detection rules',
    ],
    weaknesses: [
      'Cloud-only — data scanned on their infrastructure',
      'Heavy platform, not optimized for AI API latency',
      'Enterprise pricing — no free tier for production',
    ],
    comparisonPoints: [
      { label: 'Architecture', them: 'Cloud DLP platform (broad SaaS scanning)', us: 'Lightweight AI proxy (API-focused)' },
      { label: 'AI Focus', them: 'One of many use cases', us: 'Purpose-built for AI API privacy' },
      { label: 'Latency', them: 'Cloud processing latency', us: '<1ms local proxy' },
      { label: 'Self-Hosted', them: 'Not available', us: 'Docker deploy in 30 seconds' },
      { label: 'License', them: 'Proprietary', us: 'MIT Open Source' },
    ],
    primaryKeyword: 'Nightfall AI alternative self-hosted DLP',
  },
  {
    slug: 'private-ai',
    name: 'Private AI',
    tagline: 'On-device PII detection and redaction API',
    description:
      'Private AI provides an API and SDK for detecting and redacting PII across 50+ entity types, with on-premise deployment options for enterprise customers.',
    strengths: [
      '50+ PII entity types',
      'Multi-language support',
      'On-premise deployment available',
    ],
    weaknesses: [
      'Proprietary — not open source',
      'On-premise only on Enterprise plan',
      'Heavy resource requirements',
    ],
    comparisonPoints: [
      { label: 'Entity Coverage', them: '50+ types', us: '14+ core types, extensible via config' },
      { label: 'Open Source', them: 'Proprietary', us: 'MIT — fully open source' },
      { label: 'Pricing', them: 'Free tier limited, Enterprise expensive', us: 'Free Lite for production, affordable Pro' },
      { label: 'Deployment', them: 'SDK integration', us: 'Proxy — zero code changes needed' },
      { label: 'License', them: 'Proprietary', us: 'MIT Open Source' },
    ],
    primaryKeyword: 'Private AI open source alternative',
  },
];

export default competitors;
