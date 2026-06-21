export interface Role {
  slug: string;
  title: string;
  subtitle: string;
  painPoints: { title: string; description: string }[];
  benefits: string[];
  primaryKeyword: string;
}

const roles: Role[] = [
  {
    slug: 'cto',
    title: 'CTO',
    subtitle: 'Ship AI features fast without betting the company on data privacy',
    painPoints: [
      { title: 'Vendor Lock-in Risk', description: 'Your team wants to use 5 different AI APIs. Each has different privacy policies, data retention rules, and compliance certifications. You need a unified data protection layer.' },
      { title: 'Compliance Liability', description: 'GDPR fines up to 4% of global revenue. One engineer pasting customer data into ChatGPT could trigger an audit.' },
      { title: 'Speed vs Safety', description: 'The board wants AI features shipping monthly. Legal wants full data protection reviews. You are caught in the middle.' },
    ],
    benefits: [
      'One privacy layer for all AI APIs — no per-vendor audit',
      'Deploy in 30 seconds, not 3 months',
      'Open source MIT — no vendor risk, full code ownership',
      'GDPR/HIPAA/PIPL data minimization out of the box',
    ],
    primaryKeyword: 'AI data protection for CTO enterprise',
  },
  {
    slug: 'security-engineer',
    title: 'Security Engineer',
    subtitle: 'Protect your organization from the fastest-growing attack surface: AI API data leaks',
    painPoints: [
      { title: 'Shadow AI', description: 'Employees are using ChatGPT, Claude, and DeepSeek with corporate data. You have no visibility into what is being sent to third-party AI services.' },
      { title: 'Credential Exposure', description: 'Developers accidentally paste API keys, database connection strings, and access tokens into AI prompts while debugging.' },
      { title: 'Audit Trail Gaps', description: 'Without a centralized proxy, there is no log of what data went to which AI provider. When (not if) a breach happens, you have no forensics.' },
    ],
    benefits: [
      'Man-in-the-middle PII masking — blocks data before it reaches AI',
      'Full audit logging — every masking event recorded',
      'Zero data egress — masking happens locally, never in cloud',
      'Extensible entity detection — add custom patterns for your org',
    ],
    primaryKeyword: 'AI security engineer data leak prevention',
  },
  {
    slug: 'compliance-officer',
    title: 'Compliance Officer',
    subtitle: 'Make AI usage audit-ready without blocking innovation',
    painPoints: [
      { title: 'Regulatory Overlap', description: 'Your organization operates under GDPR, HIPAA, and possibly PIPL. Each has different data transfer requirements for AI APIs.' },
      { title: 'Data Mapping', description: 'You need to demonstrate which data flows to which AI provider, what PII is involved, and what safeguards are in place — for every integration.' },
      { title: 'Employee AI Policies', description: 'Creating AI usage policies is easy. Enforcing them technically at scale is not.' },
    ],
    benefits: [
      'Automated data minimization for all AI API traffic',
      'Audit logs suitable for SOC 2 / ISO 27001 evidence',
      'Technical enforcement of AI data handling policies',
      'Cross-border data transfer compliance (PIPL, GDPR Chapter V)',
    ],
    primaryKeyword: 'AI compliance officer GDPR HIPAA data protection',
  },
  {
    slug: 'devops-engineer',
    title: 'DevOps Engineer',
    subtitle: 'Add AI privacy to your infrastructure stack in 30 seconds',
    painPoints: [
      { title: 'Infrastructure Sprawl', description: 'You already manage proxies, load balancers, API gateways, and service meshes. Adding another layer needs to be lightweight and fit existing patterns.' },
      { title: 'Observability Integration', description: 'Any new infrastructure component must work with your existing monitoring, logging, and alerting stack.' },
      { title: 'Scaling Concerns', description: 'AI API calls are latency-sensitive. A privacy proxy must not become a bottleneck at 10K+ QPS.' },
    ],
    benefits: [
      'Single Docker container — fits existing orchestration',
      '10K+ QPS per instance, sub-1ms latency',
      'Environment-variable config — 12-factor app compatible',
      'Health check endpoint, structured logging, metrics ready',
    ],
    primaryKeyword: 'DevOps AI privacy proxy deployment infrastructure',
  },
  {
    slug: 'developer',
    title: 'Developer',
    subtitle: 'Use any AI coding tool without worrying about leaking source code or customer data',
    painPoints: [
      { title: 'AI Coding Tools Send Your Code', description: 'Cursor, Copilot, and Claude Code send your code to cloud servers. Your proprietary algorithms and business logic are being transmitted to third parties.' },
      { title: 'Debugging with Customer Data', description: 'When debugging, you paste error logs, database records, and API responses into ChatGPT. These often contain real customer PII.' },
      { title: 'API Key Exposure', description: 'Developers are the #1 source of API key leaks via AI prompts. One accidental paste can compromise production credentials.' },
    ],
    benefits: [
      'Protects source code sent to AI coding assistants',
      'Auto-masks PII in error logs and debugging data',
      'Detects and redacts API keys, tokens, and secrets',
      'Zero code changes — just change the API base URL',
    ],
    primaryKeyword: 'developer AI privacy protect source code API keys',
  },
  {
    slug: 'data-privacy-officer',
    title: 'Data Privacy Officer (DPO)',
    subtitle: 'Operationalize AI data protection across the entire organization',
    painPoints: [
      { title: 'DPIA Requirements', description: 'Data Protection Impact Assessments are mandatory for AI processing under GDPR Article 35. You need technical measures documented before signing off.' },
      { title: 'DSAR Implications', description: 'If a customer submits a Data Subject Access Request, can you identify and retrieve their data from your AI API interactions?' },
      { title: 'Processor Management', description: 'Every AI API provider is a data processor. You need to manage processor relationships, DPA agreements, and data flow documentation.' },
    ],
    benefits: [
      'Technical evidence for DPIA submissions',
      'Centralized data flow documentation for AI APIs',
      'PII masking as a documented technical safeguard',
      'Supports data minimization principle (GDPR Art. 5(1)(c))',
    ],
    primaryKeyword: 'DPO AI data protection impact assessment privacy',
  },
  {
    slug: 'healthcare-cio',
    title: 'Healthcare CIO',
    subtitle: 'Enable clinical AI adoption while maintaining ironclad PHI protection',
    painPoints: [
      { title: 'PHI in Prompts', description: 'Clinicians and researchers want to use AI for clinical notes summarization, research analysis, and patient communication — all of which involve PHI.' },
      { title: 'BAA Requirements', description: 'Most AI API providers will not sign Business Associate Agreements (BAAs). Without a BAA, you cannot send PHI to their services under HIPAA.' },
      { title: 'Vendor Risk Management', description: 'Every AI tool your staff uses needs a security review. The number of AI tools is exploding faster than your review process can handle.' },
    ],
    benefits: [
      'De-identify PHI before it reaches any AI API',
      'HIPAA-compliant architecture — data never leaves your infra',
      'One privacy layer covers all AI tools and APIs',
      'Audit logs for HIPAA Security Rule compliance',
    ],
    primaryKeyword: 'healthcare CIO HIPAA AI PHI protection LLM',
  },
  {
    slug: 'fintech-cto',
    title: 'Fintech CTO',
    subtitle: 'Leverage AI for financial services without exposing customer financial data',
    painPoints: [
      { title: 'PCI DSS and AI', description: 'Payment card data accidentally included in AI prompts creates PCI compliance violations. AI is not in your PCI scope assessment yet — but it should be.' },
      { title: 'Financial Privacy Regulations', description: 'GLBA, CCPA, and state-level financial privacy laws restrict how financial data can be shared with third parties — including AI providers.' },
      { title: 'Algorithmic Trading IP', description: 'Your quantitative models and trading strategies are your competitive edge. Sending them to AI APIs for analysis risks exposing your IP.' },
    ],
    benefits: [
      'Auto-mask payment card data, bank account numbers',
      'Protect proprietary trading algorithms and models',
      'PCI DSS scope reduction — masked data is not cardholder data',
      'Regulatory compliance for GLBA, CCPA, financial privacy laws',
    ],
    primaryKeyword: 'fintech CTO AI financial data protection PCI compliance',
  },
];

export default roles;
