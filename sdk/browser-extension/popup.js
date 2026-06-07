const enabledToggle = document.getElementById('enabledToggle');
const gatewayInput = document.getElementById('gatewayUrl');
const statusEl = document.getElementById('status');

chrome.storage.sync.get(['enabled', 'gatewayUrl'], (result) => {
  enabledToggle.checked = result.enabled !== false;
  gatewayInput.value = result.gatewayUrl || 'http://localhost:9999';
  updateStatus();
});

enabledToggle.addEventListener('change', () => {
  chrome.storage.sync.set({ enabled: enabledToggle.checked });
  updateStatus();
});

gatewayInput.addEventListener('change', () => {
  chrome.storage.sync.set({ gatewayUrl: gatewayInput.value });
});

function updateStatus() {
  if (enabledToggle.checked) {
    statusEl.textContent = '正在保护';
    statusEl.className = 'status on';
  } else {
    statusEl.textContent = '已暂停';
    statusEl.className = 'status off';
  }
}
