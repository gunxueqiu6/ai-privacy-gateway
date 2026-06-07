class PrivacyGatewayBackground {
  constructor() {
    this.gatewayUrl = 'http://localhost:9999';
    this.stats = {
      maskCount: 0,
      entityCount: 0,
      lastUpdate: Date.now()
    };
    this.init();
  }

  init() {
    this.loadSettings();
    this.createContextMenu();
    this.setupMessageListener();
  }

  async loadSettings() {
    const result = await chrome.storage.local.get(['gatewayUrl', 'enabledEntities']);
    if (result.gatewayUrl) {
      this.gatewayUrl = result.gatewayUrl;
    }
    this.enabledEntities = result.enabledEntities || {
      PII_PHONE: true,
      PII_EMAIL: true,
      PII_IDCARD: true,
      PII_PER: true,
      PII_LOC: true,
      PII_ORG: false,
      PII_BANK: true,
      PII_PLATE: false,
      PII_IP: false,
      PII_URL: false
    };
  }

  createContextMenu() {
    chrome.contextMenus.create({
      id: 'mask-selection',
      title: '复制脱敏版本',
      contexts: ['selection'],
      enabled: true
    });

    chrome.contextMenus.onClicked.addListener((info, tab) => {
      if (info.menuItemId === 'mask-selection' && info.selectionText) {
        this.handleMaskSelection(info.selectionText);
      }
    });
  }

  async handleMaskSelection(text) {
    try {
      const response = await fetch(`${this.gatewayUrl}/api/mask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      await navigator.clipboard.writeText(data.masked_text);

      this.stats.maskCount++;
      this.stats.entityCount += data.entities?.length || 0;
      this.stats.lastUpdate = Date.now();
      await this.saveStats();

      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'AI Privacy Gateway',
        message: `已复制脱敏文本到剪贴板（检测到 ${data.entities?.length || 0} 个实体）`
      });
    } catch (error) {
      console.error('Mask selection error:', error);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'AI Privacy Gateway',
        message: '脱敏失败，请确保网关服务正在运行'
      });
    }
  }

  async saveStats() {
    await chrome.storage.local.set({ privacyGatewayStats: this.stats });
  }

  async getStats() {
    const result = await chrome.storage.local.get('privacyGatewayStats');
    return result.privacyGatewayStats || this.stats;
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      switch (request.action) {
        case 'maskText':
          this.maskText(request.text).then(sendResponse);
          return true;
        case 'getStats':
          this.getStats().then(sendResponse);
          return true;
        case 'getSettings':
          this.getSettings().then(sendResponse);
          return true;
        case 'updateSettings':
          this.updateSettings(request.settings).then(sendResponse);
          return true;
        default:
          sendResponse({ error: 'Unknown action' });
      }
    });
  }

  async maskText(text) {
    try {
      const response = await fetch(`${this.gatewayUrl}/api/mask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this.stats.maskCount++;
      this.stats.entityCount += data.entities?.length || 0;
      this.stats.lastUpdate = Date.now();
      await this.saveStats();

      return data;
    } catch (error) {
      console.error('Mask text error:', error);
      return { error: error.message };
    }
  }

  async getSettings() {
    const result = await chrome.storage.local.get(['gatewayUrl', 'enabledEntities']);
    return {
      gatewayUrl: result.gatewayUrl || 'http://localhost:9999',
      enabledEntities: result.enabledEntities || this.enabledEntities
    };
  }

  async updateSettings(settings) {
    await chrome.storage.local.set({
      gatewayUrl: settings.gatewayUrl,
      enabledEntities: settings.enabledEntities
    });
    this.gatewayUrl = settings.gatewayUrl;
    this.enabledEntities = settings.enabledEntities;
    return { success: true };
  }
}

const bg = new PrivacyGatewayBackground();