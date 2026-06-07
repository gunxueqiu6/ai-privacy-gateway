const DEFAULT_GATEWAY = 'http://localhost:9999';

async function getGatewayUrl() {
  const result = await chrome.storage.sync.get('gatewayUrl');
  return result.gatewayUrl || DEFAULT_GATEWAY;
}

async function updateProxyRules() {
  const enabled = (await chrome.storage.sync.get('enabled')).enabled !== false;
  const gatewayUrl = await getGatewayUrl();

  if (!enabled) {
    await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: [1, 2, 3, 4, 5] });
    return;
  }

  const targetHosts = [
    'api.openai.com',
    'api.deepseek.com',
    'api.anthropic.com',
    'generativelanguage.googleapis.com',
  ];

  const rules = targetHosts.map((host, i) => ({
    id: i + 1,
    priority: 1,
    action: {
      type: 'redirect' as const,
      redirect: { url: `${gatewayUrl}/v1/chat/completions` },
    },
    condition: {
      urlFilter: `*://${host}/v1/chat/completions`,
      resourceTypes: ['xmlhttprequest' as const],
    },
  }));

  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [1, 2, 3, 4, 5],
    addRules: rules,
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ enabled: true, gatewayUrl: DEFAULT_GATEWAY });
  updateProxyRules();
});

chrome.runtime.onStartup.addListener(updateProxyRules);
chrome.storage.onChanged.addListener((changes) => {
  if (changes.enabled || changes.gatewayUrl) {
    updateProxyRules();
  }
});
