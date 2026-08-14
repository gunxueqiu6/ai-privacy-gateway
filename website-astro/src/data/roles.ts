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
    primaryKeyword: 'Enterprise AI Data Protection',
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
    primaryKeyword: 'AI Data Leak Prevention for Security Teams',
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
    primaryKeyword: 'GDPR and HIPAA Compliant AI Usage',
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
    primaryKeyword: 'Zero-Config AI Privacy Infrastructure',
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
    primaryKeyword: 'Protect Source Code and API Keys from AI',
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
    primaryKeyword: 'DPIA and AI Data Protection Compliance',
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
    primaryKeyword: 'HIPAA Compliant PHI Protection for AI',
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
    primaryKeyword: 'Financial Data Protection and PCI Compliance',
  },
  {
    slug: 'law-firm',
    title: '律所 / Legal Counsel',
    subtitle: '为客户部署 AI 工具前，把机密文件和数据出境风险挡在门口',
    painPoints: [
      { title: 'Confidential Documents in AI', description: '律师和助理把合同、证词、尽调材料投给 ChatGPT/Claude 做摘要和审查，客户机密和律师-客户特权信息随之出境。' },
      { title: 'Cross-border Data Transfer', description: '跨境传输客户数据触及 PIPL/DSL、GDPR Chapter V 等合规义务，律所需要可审计的技术控制来证明数据最小化。' },
      { title: 'Discovery & Privilege Risk', description: 'AI 工具的数据留存和训练条款可能使特权信息进入不可控存储，无法在审计和取证时自证清白。' },
    ],
    benefits: [
      '本地脱敏后才转发到 AI 提供商，机密文件不出境',
      '逐条决策审计记录，可导出签名证据包应对审计',
      '多法域合规（PIPL/GDPR/HIPAA）技术控制开箱即用',
      '覆盖中文证件/统一社会信用代码等西方法域工具易漏的实体',
    ],
    primaryKeyword: 'Law Firm AI Confidentiality and Cross-border Compliance',
  },
  {
    slug: 'china-dpo',
    title: '中国数据合规官 / China DPO',
    subtitle: '在《个人信息保护法》和《数据安全法》下，管住 AI 工具的跨境数据出口',
    painPoints: [
      { title: 'PIPL 出境合规', description: '员工用 Cursor/Claude Code/ChatGPT 时把代码、客户个人信息、内部数据传到境外，触发数据出境安全评估/标准合同义务。' },
      { title: '重要数据分级', description: '需要识别并分级「个人信息 / 重要数据 / 核心数据」，并对出境行为留痕——手工几乎不可行。' },
      { title: '技术留痕缺失', description: '没有网关，就无法证明「什么数据、何时、发给了哪家境外 AI」，一旦被查无法举证。' },
    ],
    benefits: [
      '中文实体深度识别（身份证/统一社会信用代码/港澳台证件/车牌）',
      '数据分级（personal_info/important_data/core_data）自动打标',
      '逐条出境审计 + 可签名证据导出，满足留痕举证要求',
      '本地部署，数据不出内网，符合《数据安全法》要求',
    ],
    primaryKeyword: 'PIPL 数据出境合规 AI 网关',
  },
];

export default roles;
