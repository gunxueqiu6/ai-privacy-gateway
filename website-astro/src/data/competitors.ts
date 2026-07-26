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
      { label: 'License', them: 'Proprietary', us: 'PolyForm Shield' },
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
      { label: 'License', them: 'MIT', us: 'PolyForm Shield' },
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
      { label: 'Open Source', them: 'Proprietary', us: 'PolyForm Shield — source available' },
      { label: 'License', them: 'Proprietary', us: 'PolyForm Shield' },
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
      { label: 'License', them: 'Apache 2.0', us: 'PolyForm Shield' },
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
      { label: 'License', them: 'Proprietary SaaS', us: 'PolyForm Shield' },
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
      { label: 'License', them: 'Proprietary', us: 'PolyForm Shield' },
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
      { label: 'Open Source', them: 'Proprietary', us: 'PolyForm Shield — source available' },
      { label: 'Pricing', them: 'Free tier limited, Enterprise expensive', us: 'Free Lite for production, affordable Pro' },
      { label: 'Deployment', them: 'SDK integration', us: 'Proxy — zero code changes needed' },
      { label: 'License', them: 'Proprietary', us: 'PolyForm Shield' },
    ],
    primaryKeyword: 'Private AI open source alternative',
  },
  {
    slug: 'presidio',
    name: 'Microsoft Presidio',
    tagline: 'Open-source PII detection and anonymization library by Microsoft',
    description:
      'Microsoft Presidio is an open-source library for context-aware PII detection and anonymization of text and images. It provides a modular framework with pluggable detection and anonymization components.',
    strengths: [
      'Context-aware entity detection with analyzers',
      'Modular architecture with pluggable components',
      'Image redaction support (PII in images)',
    ],
    weaknesses: [
      'Library integration required — no proxy/gateway',
      'Python-only — no cross-platform deployment',
      'No streaming/SSE support for real-time masking',
    ],
    comparisonPoints: [
      { label: 'Architecture', them: 'Python library (code integration)', us: 'Standalone proxy (zero code changes)' },
      { label: 'Deployment', them: 'pip install + code changes', us: '30-second Docker deploy, change base URL' },
      { label: 'Real-time Proxy', them: 'Not available', us: 'Full SSE streaming with live masking' },
      { label: 'Performance', them: 'Python-based processing', us: 'Rust engine — sub-1ms latency' },
      { label: 'License', them: 'MIT', us: 'PolyForm Shield' },
    ],
    primaryKeyword: 'Microsoft Presidio vs AI Privacy Gateway comparison',
  },
  {
    slug: 'kiji-proxy',
    name: 'Kiji Proxy',
    tagline: 'Open-source AI data leak prevention proxy',
    description:
      'Kiji Proxy is an open-source proxy that monitors and controls data sent to AI APIs. It focuses on data loss prevention for enterprise AI usage with policy-based filtering.',
    strengths: [
      'Policy-based data filtering and control',
      'Open source with community contributions',
      'Enterprise-focused DLP features',
    ],
    weaknesses: [
      'Limited PII entity detection coverage',
      'Requires policy configuration for each use case',
      'Less mature ecosystem and documentation',
    ],
    comparisonPoints: [
      { label: 'PII Detection', them: 'Basic regex-based detection', us: 'Regex + NER dual engine — 14 entity types' },
      { label: 'Deployment', them: 'Docker with config setup', us: '30-second Docker — zero config required' },
      { label: 'SSE Streaming', them: 'Limited support', us: 'Full SSE proxy with real-time masking' },
      { label: 'Performance', them: 'Moderate latency', us: 'Sub-1ms Rust engine' },
      { label: 'License', them: 'Apache 2.0', us: 'PolyForm Shield' },
    ],
    primaryKeyword: 'Kiji Proxy vs AI Privacy Gateway alternative',
  },
  {
    slug: 'ai-firewall',
    name: 'AI Firewall',
    tagline: 'Cloud-based AI safety and security filtering platform',
    description:
      'AI Firewall is a cloud-based security platform that filters prompts and responses for AI applications, providing content moderation, PII detection, and threat prevention as a managed service.',
    strengths: [
      'Cloud-managed — no infrastructure to maintain',
      'Content moderation and safety filters',
      'Threat intelligence integration',
    ],
    weaknesses: [
      'Cloud-only — data processed on external servers',
      'Subscription-based pricing can be costly',
      'No self-hosted deployment option',
    ],
    comparisonPoints: [
      { label: 'Data Residency', them: 'Data processed in cloud', us: '100% local — data never leaves your infra' },
      { label: 'Deployment', them: 'Cloud API integration', us: 'Self-hosted Docker, 30-second deploy' },
      { label: 'Pricing', them: 'Per-request subscription', us: 'Free Lite, flat pricing for Pro' },
      { label: 'Open Source', them: 'Proprietary', us: 'PolyForm Shield — source available' },
      { label: 'Offline Support', them: 'Requires internet', us: 'Fully offline capable' },
    ],
    primaryKeyword: 'AI Firewall self-hosted alternative open source',
  },
  {
    slug: 'llm-sentinel',
    name: 'LLM Sentinel',
    tagline: 'AI prompt security gateway with real-time threat detection',
    description:
      'LLM Sentinel is a security gateway for LLM applications that provides prompt injection detection, data loss prevention, and PII redaction as a managed proxy service.',
    strengths: [
      'Advanced prompt injection detection',
      'Real-time threat monitoring dashboard',
      'Managed service with quick setup',
    ],
    weaknesses: [
      'Cloud-managed — no self-hosting option',
      'Per-request pricing scales poorly',
      'Limited PII entity coverage compared to alternatives',
    ],
    comparisonPoints: [
      { label: 'Self-Hosted', them: 'Not available', us: 'Docker, binary, any environment' },
      { label: 'PII Coverage', them: 'Basic entity types', us: '14+ types including Chinese formats' },
      { label: 'Latency', them: 'Cloud round-trip latency', us: 'Sub-1ms local processing' },
      { label: 'Pricing Model', them: 'Per-request billing', us: 'Free Lite, flat-rate Pro' },
      { label: 'License', them: 'Proprietary SaaS', us: 'PolyForm Shield' },
    ],
    primaryKeyword: 'LLM Sentinel open source alternative self-hosted',
  },
];

export default competitors;
