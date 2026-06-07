class OptionsHandler {
  constructor() {
    this.entityTypes = [
      { key: 'PII_PHONE', name: '手机号', description: '中国大陆手机号' },
      { key: 'PII_EMAIL', name: '邮箱', description: '电子邮箱地址' },
      { key: 'PII_IDCARD', name: '身份证', description: '中国身份证号码' },
      { key: 'PII_PER', name: '人名', description: '中文人名' },
      { key: 'PII_LOC', name: '地名', description: '省份、城市等' },
      { key: 'PII_ORG', name: '机构名', description: '公司、组织名称' },
      { key: 'PII_BANK', name: '银行卡', description: '银行卡号码' },
      { key: 'PII_PLATE', name: '车牌号', description: '中国车牌号' },
      { key: 'PII_IP', name: 'IP地址', description: 'IPv4 地址' },
      { key: 'PII_URL', name: 'URL', description: '网址链接' },
    ];

    this.customKeywords = [];
    this.enabledEntities = {};
    this.gatewayUrl = 'http://localhost:9999';

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadSettings();
  }

  setupEventListeners() {
    document.getElementById('saveBtn').addEventListener('click', () => {
      this.saveSettings();
    });

    document.getElementById('resetBtn').addEventListener('click', () => {
      this.resetSettings();
    });

    document.getElementById('addKeyword').addEventListener('click', () => {
      this.addKeyword();
    });

    document.getElementById('keywordInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        this.addKeyword();
      }
    });
  }

  async loadSettings() {
    const response = await chrome.runtime.sendMessage({ action: 'getSettings' });

    if (response) {
      this.gatewayUrl = response.gatewayUrl || 'http://localhost:9999';
      this.enabledEntities = response.enabledEntities || {};
      document.getElementById('gatewayUrl').value = this.gatewayUrl;
    }

    const keywordsResult = await chrome.storage.local.get('customKeywords');
    this.customKeywords = keywordsResult.customKeywords || [];

    this.renderEntityList();
    this.renderKeywords();
    this.loadStats();
  }

  async loadStats() {
    const result = await chrome.storage.local.get('privacyGatewayStats');
    const stats = result.privacyGatewayStats || { maskCount: 0, entityCount: 0, lastUpdate: 0 };
    const isActive = stats.lastUpdate && (Date.now() - stats.lastUpdate < 300000);

    document.getElementById('totalMasked').textContent = stats.maskCount;
    document.getElementById('totalEntities').textContent = stats.entityCount;
    document.getElementById('lastUpdated').textContent = stats.lastUpdate
      ? new Date(stats.lastUpdate).toLocaleString('zh-CN')
      : '暂无数据';
    document.getElementById('activeStatus').textContent = isActive ? '保护中' : '待启用';
    document.getElementById('activeStatus').style.color = isActive ? '#10b981' : '#999';
  }

  renderEntityList() {
    const container = document.getElementById('entityList');
    container.innerHTML = '';

    this.entityTypes.forEach((entity) => {
      const item = document.createElement('div');
      item.className = 'entity-item';
      
      const labelDiv = document.createElement('div');
      labelDiv.className = 'entity-label';
      labelDiv.innerHTML = `<div style="font-weight: 500;">${entity.name}</div>
                           <div class="entity-description">${entity.description}</div>`;
      
      const switchEl = document.createElement('div');
      switchEl.className = 'switch';
      switchEl.dataset.key = entity.key;
      
      if (this.enabledEntities[entity.key] !== false) {
        switchEl.classList.add('active');
        this.enabledEntities[entity.key] = true;
      }
      
      switchEl.addEventListener('click', () => {
        switchEl.classList.toggle('active');
        this.enabledEntities[entity.key] = switchEl.classList.contains('active');
      });
      
      item.appendChild(labelDiv);
      item.appendChild(switchEl);
      container.appendChild(item);
    });
  }

  renderKeywords() {
    const container = document.getElementById('keywordsList');
    container.innerHTML = '';

    this.customKeywords.forEach((keyword, index) => {
      const tag = document.createElement('div');
      tag.className = 'keyword-tag';
      tag.innerHTML = `
        <span>${keyword}</span>
        <button data-index="${index}">×</button>
      `;
      
      tag.querySelector('button').addEventListener('click', (e) => {
        const idx = parseInt(e.target.dataset.index);
        this.customKeywords.splice(idx, 1);
        this.renderKeywords();
      });
      
      container.appendChild(tag);
    });

    if (this.customKeywords.length === 0) {
      container.innerHTML = '<span style="color: #999; font-size: 13px;">暂无自定义敏感词</span>';
    }
  }

  addKeyword() {
    const input = document.getElementById('keywordInput');
    const keyword = input.value.trim();
    
    if (keyword && !this.customKeywords.includes(keyword)) {
      this.customKeywords.push(keyword);
      input.value = '';
      this.renderKeywords();
    }
  }

  async saveSettings() {
    const gatewayUrl = document.getElementById('gatewayUrl').value.trim();
    
    if (!gatewayUrl) {
      this.showMessage('请输入网关地址', 'error');
      return;
    }

    try {
      await chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: {
          gatewayUrl,
          enabledEntities: this.enabledEntities
        }
      });

      await chrome.storage.local.set({ customKeywords: this.customKeywords });

      this.showMessage('设置保存成功', 'success');
    } catch (error) {
      this.showMessage('保存失败: ' + error.message, 'error');
    }
  }

  async resetSettings() {
    this.gatewayUrl = 'http://localhost:9999';
    this.enabledEntities = {
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
    this.customKeywords = [];

    document.getElementById('gatewayUrl').value = this.gatewayUrl;
    this.renderEntityList();
    this.renderKeywords();

    await chrome.runtime.sendMessage({
      action: 'updateSettings',
      settings: {
        gatewayUrl: this.gatewayUrl,
        enabledEntities: this.enabledEntities
      }
    });

    await chrome.storage.local.set({ customKeywords: [] });

    this.showMessage('已重置为默认设置', 'success');
  }

  showMessage(message, type) {
    const el = document.getElementById('statusMessage');
    el.textContent = message;
    el.className = `status-message ${type}`;
    
    setTimeout(() => {
      el.className = 'status-message';
    }, 3000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new OptionsHandler();
});