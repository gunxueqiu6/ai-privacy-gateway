class PrivacyGatewayContent {
  constructor() {
    this.isMaskEnabled = true;
    this.gatewayUrl = 'http://localhost:9999';
    this.currentPage = this.detectPage();
    this.init();
  }

  detectPage() {
    const url = window.location.href;
    if (url.includes('chat.openai.com')) return 'chatgpt';
    if (url.includes('claude.ai')) return 'claude';
    if (url.includes('kimi.moonshot')) return 'kimi';
    if (url.includes('deepseek')) return 'deepseek';
    if (url.includes('yuanbao')) return 'yuanbao';
    if (url.includes('doubao')) return 'doubao';
    return 'unknown';
  }

  async init() {
    await this.loadSettings();
    this.createToggleButton();
    this.setupMessageListener();
    this.setupPageListeners();
  }

  async loadSettings() {
    const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
    if (response) {
      this.gatewayUrl = response.gatewayUrl || 'http://localhost:9999';
    }
  }

  createToggleButton() {
    const button = document.createElement('button');
    button.id = 'privacy-gateway-toggle';
    button.className = 'privacy-gateway-btn';
    button.innerHTML = this.isMaskEnabled 
      ? '<span>🔒</span> 脱敏开启' 
      : '<span>🔓</span> 脱敏关闭';
    button.title = '点击切换敏感信息脱敏';
    
    button.addEventListener('click', () => {
      this.isMaskEnabled = !this.isMaskEnabled;
      button.innerHTML = this.isMaskEnabled 
        ? '<span>🔒</span> 脱敏开启' 
        : '<span>🔓</span> 脱敏关闭';
      
      if (this.isMaskEnabled) {
        button.classList.add('enabled');
        button.classList.remove('disabled');
      } else {
        button.classList.remove('enabled');
        button.classList.add('disabled');
      }
    });

    this.injectButton(button);
  }

  injectButton(button) {
    const style = document.createElement('style');
    style.textContent = `
      .privacy-gateway-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        padding: 12px 20px;
        border: none;
        border-radius: 25px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .privacy-gateway-btn.enabled {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
      }

      .privacy-gateway-btn.disabled {
        background: linear-gradient(135deg, #6b7280, #4b5563);
        color: white;
      }

      .privacy-gateway-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
      }

      .privacy-gateway-btn span {
        font-size: 16px;
      }

      .privacy-gateway-highlight {
        background-color: rgba(248, 215, 218, 0.8) !important;
        border-bottom: 2px solid #ef4444 !important;
        border-radius: 2px;
        padding: 0 2px;
      }
    `;
    document.head.appendChild(style);
    document.body.appendChild(button);
  }

  setupPageListeners() {
    switch (this.currentPage) {
      case 'chatgpt':
        this.setupChatGPTListener();
        break;
      case 'claude':
        this.setupClaudeListener();
        break;
      case 'kimi':
        this.setupKimiListener();
        break;
      case 'deepseek':
        this.setupDeepseekListener();
        break;
      default:
        this.setupGenericListener();
    }
    this.setupEntityHighlightListener();
  }

  setupEntityHighlightListener() {
    // 监听全局 input 事件，实时高亮检测到的实体
    document.addEventListener('input', (e) => {
      if (!this.isMaskEnabled) return;
      const target = e.target;
      if (target.tagName === 'TEXTAREA' || (target.tagName === 'INPUT' && target.type === 'text')) {
        this.showEntityDetection(target);
      }
    }, true);

    // 也监听 focusin 以在聚焦输入框时显示检测
    document.addEventListener('focusin', (e) => {
      if (!this.isMaskEnabled) return;
      const target = e.target;
      if (target.tagName === 'TEXTAREA' || (target.tagName === 'INPUT' && target.type === 'text')) {
        if (target.value && target.value.trim()) {
          this.showEntityDetection(target);
        }
      }
    }, true);
  }

  showEntityDetection(inputEl) {
    const text = inputEl.value;
    if (!text || !text.trim()) {
      this.removeDetectionBadge();
      return;
    }

    const entityPatterns = [
      { pattern: /1[3-9]\d{9}/g, label: '手机号' },
      { pattern: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, label: '邮箱' },
      { pattern: /[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]/g, label: '身份证' },
      { pattern: /\b([1-9]\d{15,18})\b/g, label: '银行卡' },
    ];

    const detected = [];
    entityPatterns.forEach(({ pattern, label }) => {
      const matches = text.match(pattern);
      if (matches) {
        detected.push({ label, count: matches.length, examples: matches.slice(0, 2) });
      }
    });

    if (detected.length > 0) {
      this.showDetectionBadge(detected, inputEl);
    } else {
      this.removeDetectionBadge();
    }
  }

  showDetectionBadge(detected, inputEl) {
    let badge = document.getElementById('privacy-gateway-detection-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.id = 'privacy-gateway-detection-badge';
      badge.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 20px;
        z-index: 9998;
        background: rgba(239, 68, 68, 0.95);
        color: white;
        padding: 8px 14px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        max-width: 220px;
        line-height: 1.5;
      `;
      document.body.appendChild(badge);
    }

    const totalCount = detected.reduce((sum, d) => sum + d.count, 0);
    const items = detected.map(d =>
      `<div style="display:flex;justify-content:space-between;gap:12px"><span>${d.label}</span><span>${d.count}个</span></div>`
    ).join('');

    badge.innerHTML = `
      <div style="margin-bottom:4px">检测到 ${totalCount} 个敏感实体</div>
      ${items}
    `;
  }

  removeDetectionBadge() {
    const badge = document.getElementById('privacy-gateway-detection-badge');
    if (badge) badge.remove();
  }

  setupChatGPTListener() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.querySelector?.('[data-testid="send-button"]')) {
            this.attachSendInterceptor(node);
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  setupClaudeListener() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        const textarea = document.querySelector('textarea');
        if (textarea && this.isMaskEnabled) {
          this.handleSend(textarea);
        }
      }
    });
  }

  setupKimiListener() {
    document.addEventListener('click', (e) => {
      if (e.target.closest('button')?.textContent.includes('发送')) {
        const textarea = document.querySelector('textarea');
        if (textarea && this.isMaskEnabled) {
          this.handleSend(textarea);
        }
      }
    });
  }

  setupDeepseekListener() {
    document.addEventListener('click', (e) => {
      if (e.target.closest('[role="button"]')?.textContent.includes('发送')) {
        const textarea = document.querySelector('textarea');
        if (textarea && this.isMaskEnabled) {
          this.handleSend(textarea);
        }
      }
    });
  }

  setupGenericListener() {
    document.addEventListener('click', (e) => {
      const sendButton = e.target.closest('button');
      if (sendButton && sendButton.textContent.includes('发送')) {
        const textarea = document.querySelector('textarea');
        if (textarea && this.isMaskEnabled) {
          this.handleSend(textarea);
        }
      }
    });
  }

  attachSendInterceptor(container) {
    const sendButton = container.querySelector('[data-testid="send-button"]');
    if (sendButton && !sendButton.hasListener) {
      sendButton.hasListener = true;
      sendButton.addEventListener('click', (e) => {
        if (this.isMaskEnabled) {
          const textarea = document.querySelector('textarea');
          if (textarea) {
            this.handleSend(textarea);
          }
        }
      });
    }
  }

  async handleSend(textarea) {
    const originalText = textarea.value;
    if (!originalText.trim()) return;

    try {
      const response = await chrome.runtime.sendMessage({
        action: 'maskText',
        text: originalText
      });

      if (response && response.masked_text) {
        textarea.value = response.masked_text;
        setTimeout(() => {
          textarea.value = originalText;
        }, 100);
      }
    } catch (error) {
      console.error('Mask send error:', error);
    }
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      switch (request.action) {
        case 'toggleMask':
          this.isMaskEnabled = request.enabled;
          const button = document.getElementById('privacy-gateway-toggle');
          if (button) {
            button.innerHTML = this.isMaskEnabled 
              ? '<span>🔒</span> 脱敏开启' 
              : '<span>🔓</span> 脱敏关闭';
          }
          sendResponse({ success: true });
          break;
        case 'getState':
          sendResponse({ isMaskEnabled: this.isMaskEnabled });
          break;
        default:
          sendResponse({ error: 'Unknown action' });
      }
    });
  }

  highlightEntities(text) {
    const entityPatterns = [
      { pattern: /1[3-9]\d{9}/g, type: 'phone' },
      { pattern: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, type: 'email' },
      { pattern: /[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]/g, type: 'idcard' },
    ];

    let highlighted = text;
    entityPatterns.forEach(({ pattern, type }) => {
      highlighted = highlighted.replace(pattern, (match) => {
        return `<span class="privacy-gateway-highlight" title="${type}">${match}</span>`;
      });
    });

    return highlighted;
  }
}

const content = new PrivacyGatewayContent();