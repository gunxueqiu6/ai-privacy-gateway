class PrivacyGatewayContent {
  constructor() {
    this.isMaskEnabled = true;
    this.gatewayUrl = 'http://localhost:9999';
    this.currentPage = this.detectPage();
    this.init();
  }

  detectPage() {
    const url = window.location.href;
    if (url.includes('chat.openai.com') || url.includes('chatgpt.com')) return 'chatgpt';
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
    button.title = '点击切换敏感信息脱敏';
    this.updateToggleButton(button);

    button.addEventListener('click', () => {
      this.isMaskEnabled = !this.isMaskEnabled;
      this.updateToggleButton(button);

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

  updateToggleButton(button) {
    const span = document.createElement('span');
    span.textContent = this.isMaskEnabled ? '🔒' : '🔓';
    button.textContent = '';
    button.appendChild(span);
    button.appendChild(document.createTextNode(this.isMaskEnabled ? ' 脱敏开启' : ' 脱敏关闭'));
  }

  injectButton(button) {
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
    // AI chat input selector whitelist
    const AI_INPUT_SELECTORS = [
      '.ProseMirror',          // ChatGPT
      '[contenteditable]',      // Claude and other editable divs
      'textarea',               // Generic AI chat textareas
      'input[type="text"]',     // Generic text inputs
    ];

    const isAiChatInput = (el) => {
      // Never monitor password fields
      if (el.type === 'password') return false;
      if (el.tagName === 'INPUT' && !el.matches('input[type="text"], input:not([type])')) return false;
      return AI_INPUT_SELECTORS.some(sel => el.matches(sel) || el.closest(sel));
    };

    // 监听全局 input 事件，实时高亮检测到的实体
    document.addEventListener('input', (e) => {
      if (!this.isMaskEnabled) return;
      const target = e.target;
      if (isAiChatInput(target)) {
        this.showEntityDetection(target);
      }
    }, true);

    // 也监听 focusin 以在聚焦输入框时显示检测
    document.addEventListener('focusin', (e) => {
      if (!this.isMaskEnabled) return;
      const target = e.target;
      if (isAiChatInput(target)) {
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
      document.body.appendChild(badge);
    }

    const totalCount = detected.reduce((sum, d) => sum + d.count, 0);

    badge.textContent = '';
    const header = document.createElement('div');
    header.style.marginBottom = '4px';
    header.textContent = `检测到 ${totalCount} 个敏感实体`;
    badge.appendChild(header);

    detected.forEach(d => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.gap = '12px';
      const labelSpan = document.createElement('span');
      labelSpan.textContent = d.label;
      const countSpan = document.createElement('span');
      countSpan.textContent = `${d.count}个`;
      row.appendChild(labelSpan);
      row.appendChild(countSpan);
      badge.appendChild(row);
    });
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
        textarea.dataset.privacyOriginal = originalText;
        // Restore original after the page's native send handler reads the masked value
        setTimeout(() => {
          if (textarea.value !== originalText && textarea.value !== '') {
            textarea.value = textarea.dataset.privacyOriginal || originalText;
          }
          delete textarea.dataset.privacyOriginal;
        }, 500);
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
            this.updateToggleButton(button);
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

    // Split text into segments: entity matches (to wrap) and non-matches (plain text)
    const allMatches = [];
    entityPatterns.forEach(({ pattern, type }) => {
      // Reset lastIndex and clone to avoid cross-pattern interference
      const p = new RegExp(pattern.source, 'g');
      let match;
      while ((match = p.exec(text)) !== null) {
        allMatches.push({ start: match.index, end: match.index + match[0].length, type, value: match[0] });
      }
    });

    if (allMatches.length === 0) return text;

    allMatches.sort((a, b) => a.start - b.start);

    // Merge overlapping ranges
    const merged = [];
    for (const m of allMatches) {
      if (merged.length > 0 && m.start <= merged[merged.length - 1].end) {
        if (m.end > merged[merged.length - 1].end) {
          merged[merged.length - 1].end = m.end;
        }
      } else {
        merged.push({ start: m.start, end: m.end, type: m.type });
      }
    }

    // Build result as DOM nodes
    const container = document.createElement('div');
    let lastIndex = 0;
    merged.forEach(({ start, end, type }) => {
      if (start > lastIndex) {
        container.appendChild(document.createTextNode(text.slice(lastIndex, start)));
      }
      const span = document.createElement('span');
      span.className = 'privacy-gateway-highlight';
      span.title = type;
      span.textContent = text.slice(start, end);
      container.appendChild(span);
      lastIndex = end;
    });
    if (lastIndex < text.length) {
      container.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    return container.innerHTML;
  }
}

const content = new PrivacyGatewayContent();