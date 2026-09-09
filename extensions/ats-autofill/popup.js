document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-gear').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  const enableBtn = document.getElementById('btn-enable');
  const statusEl = document.getElementById('enable-status');
  function setStatus(text, isErr) {
    if (!statusEl) return;
    statusEl.hidden = false;
    statusEl.textContent = text;
    statusEl.className = 'status' + (isErr ? ' err' : '');
  }
  if (enableBtn) {
    enableBtn.addEventListener('click', async () => {
      try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        const tab = tabs && tabs[0];
        if (!tab || !tab.url || !/^https?:/i.test(tab.url)) {
          setStatus('请先打开网申页（http/https）', true);
          return;
        }
        const origin = new URL(tab.url).origin;
        const granted = await chrome.permissions.request({ origins: [origin + '/*'] });
        if (!granted) {
          setStatus('未授予该网站权限', true);
          return;
        }
        chrome.runtime.sendMessage({ action: 'ENABLE_ON_ACTIVE_TAB' }, (res) => {
          if (!res || !res.ok) {
            setStatus((res && res.error) || '注入失败', true);
            return;
          }
          setStatus('已在 ' + (res.host || origin) + ' 启用。打开报名表再一键填充。');
        });
      } catch (err) {
        setStatus(String(err && err.message ? err.message : err), true);
      }
    });
  }

  const table = document.getElementById('shortcut-table');
  const api = self.CareerOsShortcuts;
  if (!api) return;
  api.load().then((map) => {
    table.textContent = '';
    Object.keys(api.DEFAULTS).forEach((id) => {
      const s = map[id];
      const tr = document.createElement('tr');
      const k = document.createElement('td');
      k.className = 'k';
      k.textContent = api.format(s);
      const l = document.createElement('td');
      l.className = 'l';
      l.textContent = s.label;
      tr.appendChild(k);
      tr.appendChild(l);
      table.appendChild(tr);
    });
  });
});
