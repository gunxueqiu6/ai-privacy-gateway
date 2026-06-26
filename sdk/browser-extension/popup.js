class PopupHandler {
  constructor() {
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadStats();
    this.checkGatewayStatus();
    this.loadMaskState();
  }

  setupEventListeners() {
    document.getElementById('maskToggle').addEventListener('click', () => {
      this.toggleMask();
    });

    document.getElementById('openOptions').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });

    document.getElementById('openDocs').addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://privacygw.pages.dev/docs' });
    });
  }

  async loadStats() {
    const response = await chrome.runtime.sendMessage({ action: 'getStats' });
    if (response) {
      document.getElementById('maskCount').textContent = response.maskCount || 0;
      document.getElementById('entityCount').textContent = response.entityCount || 0;
      
      if (response.lastUpdate) {
        const date = new Date(response.lastUpdate);
        document.getElementById('lastUpdate').textContent = date.toLocaleString('zh-CN');
      }
    }
  }

  async checkGatewayStatus() {
    const settings = await chrome.runtime.sendMessage({ action: 'getSettings' });
    const gatewayUrl = settings?.gatewayUrl || 'http://localhost:9999';

    try {
      const response = await fetch(`${gatewayUrl}/health`);
      if (response.ok) {
        this.setGatewayStatus(true, '网关已连接');
      } else {
        this.setGatewayStatus(false, '网关未响应');
      }
    } catch (error) {
      this.setGatewayStatus(false, '网关不可达');
    }
  }

  setGatewayStatus(online, message) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    
    if (online) {
      dot.classList.add('online');
    } else {
      dot.classList.remove('online');
    }
    text.textContent = message;
  }

  async loadMaskState() {
    // Load persisted state first, then sync with active tab
    const stored = await chrome.storage.local.get('maskEnabled');
    const persisted = stored.maskEnabled !== undefined ? stored.maskEnabled : true;
    this.updateToggle(persisted);

    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      try {
        const response = await chrome.tabs.sendMessage(tabs[0].id, { action: 'getState' });
        if (response) {
          this.updateToggle(response.isMaskEnabled);
        }
      } catch (_) {
        // Content script not available, use persisted state
      }
    }
  }

  async toggleMask() {
    const toggle = document.getElementById('maskToggle');
    const isEnabled = !toggle.classList.contains('active');

    this.updateToggle(isEnabled);

    // Persist state
    await chrome.storage.local.set({ maskEnabled: isEnabled });

    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      try {
        await chrome.tabs.sendMessage(tabs[0].id, {
          action: 'toggleMask',
          enabled: isEnabled
        });
      } catch (_) {
        // Content script not available
      }
    }
  }

  updateToggle(isEnabled) {
    const toggle = document.getElementById('maskToggle');
    if (isEnabled) {
      toggle.classList.add('active');
    } else {
      toggle.classList.remove('active');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new PopupHandler();
});